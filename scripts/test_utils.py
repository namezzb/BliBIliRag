#!/usr/bin/env python3
"""
B站 RAG 项目测试工具
支持：并发测试、性能分析、数据库验证、日志分析
"""

import asyncio
import time
import json
import sqlite3
import argparse
import statistics
from pathlib import Path
from typing import List, Dict, Any
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
BASE_URL = "http://localhost:8000"
DB_PATH = "data/bilibilirag.db"
TIMEOUT = 30


class TestRunner:
    """测试运行器"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.results = []
        self.timings = []

    def test_endpoint(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """测试单个端点"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            if method == "GET":
                response = requests.get(url, timeout=TIMEOUT)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=TIMEOUT)
            elif method == "DELETE":
                response = requests.delete(url, timeout=TIMEOUT)
            else:
                raise ValueError(f"Unsupported method: {method}")

            elapsed = time.time() - start_time
            self.timings.append(elapsed)

            return {
                "method": method,
                "endpoint": endpoint,
                "status": response.status_code,
                "time": elapsed,
                "success": 200 <= response.status_code < 300,
                "response": response.text[:200] if response.text else "",
            }
        except Exception as e:
            elapsed = time.time() - start_time
            return {
                "method": method,
                "endpoint": endpoint,
                "status": 0,
                "time": elapsed,
                "success": False,
                "error": str(e),
            }

    def concurrent_test(self, method: str, endpoint: str, count: int = 10) -> List[Dict]:
        """并发测试"""
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(self.test_endpoint, method, endpoint)
                for _ in range(count)
            ]
            for future in as_completed(futures):
                results.append(future.result())
        return results

    def load_test(self, duration: int = 60, concurrent: int = 5) -> Dict[str, Any]:
        """负载测试"""
        print(f"Running load test for {duration} seconds with {concurrent} concurrent connections...")

        start_time = time.time()
        request_count = 0
        success_count = 0
        error_count = 0
        timings = []

        with ThreadPoolExecutor(max_workers=concurrent) as executor:
            futures = []

            while time.time() - start_time < duration:
                # Submit new requests
                while len(futures) < concurrent:
                    future = executor.submit(self.test_endpoint, "GET", "/health")
                    futures.append(future)

                # Check completed futures
                done_futures = [f for f in futures if f.done()]
                for future in done_futures:
                    result = future.result()
                    request_count += 1
                    if result["success"]:
                        success_count += 1
                    else:
                        error_count += 1
                    timings.append(result["time"])
                    futures.remove(future)

                time.sleep(0.1)

        elapsed = time.time() - start_time

        return {
            "duration": elapsed,
            "total_requests": request_count,
            "successful": success_count,
            "failed": error_count,
            "success_rate": (success_count / request_count * 100) if request_count > 0 else 0,
            "avg_time": statistics.mean(timings) if timings else 0,
            "min_time": min(timings) if timings else 0,
            "max_time": max(timings) if timings else 0,
            "median_time": statistics.median(timings) if timings else 0,
            "requests_per_second": request_count / elapsed if elapsed > 0 else 0,
        }

    def print_results(self, results: List[Dict]):
        """打印测试结果"""
        print("\n" + "=" * 80)
        print("Test Results")
        print("=" * 80)

        for result in results:
            status_symbol = "✓" if result["success"] else "✗"
            print(
                f"{status_symbol} {result['method']:6} {result['endpoint']:30} "
                f"Status: {result['status']:3} Time: {result['time']:.3f}s"
            )

        if self.timings:
            print("\n" + "-" * 80)
            print(f"Average response time: {statistics.mean(self.timings):.3f}s")
            print(f"Median response time: {statistics.median(self.timings):.3f}s")
            print(f"Min response time: {min(self.timings):.3f}s")
            print(f"Max response time: {max(self.timings):.3f}s")


class DatabaseValidator:
    """数据库验证器"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)

    def validate_schema(self) -> Dict[str, Any]:
        """验证数据库架构"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        schema = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table});")
            columns = cursor.fetchall()
            schema[table] = [col[1] for col in columns]

        conn.close()
        return schema

    def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        conn = self.get_connection()
        cursor = conn.cursor()

        stats = {}

        # Count records in each table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            stats[table] = count

        conn.close()
        return stats

    def validate_data_consistency(self) -> Dict[str, Any]:
        """验证数据一致性"""
        conn = self.get_connection()
        cursor = conn.cursor()

        issues = []

        # Check for orphaned records
        cursor.execute("""
            SELECT COUNT(*) FROM subtitles
            WHERE video_id NOT IN (SELECT id FROM videos)
        """)
        orphaned_subtitles = cursor.fetchone()[0]
        if orphaned_subtitles > 0:
            issues.append(f"Found {orphaned_subtitles} orphaned subtitle records")

        # Check for missing required fields
        cursor.execute("SELECT COUNT(*) FROM videos WHERE title IS NULL OR title = '';")
        missing_titles = cursor.fetchone()[0]
        if missing_titles > 0:
            issues.append(f"Found {missing_titles} videos with missing titles")

        conn.close()

        return {
            "is_consistent": len(issues) == 0,
            "issues": issues,
        }

    def print_statistics(self):
        """打印数据库统计信息"""
        print("\n" + "=" * 80)
        print("Database Statistics")
        print("=" * 80)

        schema = self.validate_schema()
        print("\nTables and Columns:")
        for table, columns in schema.items():
            print(f"  {table}: {', '.join(columns)}")

        stats = self.get_statistics()
        print("\nRecord Counts:")
        for table, count in stats.items():
            print(f"  {table}: {count}")

        consistency = self.validate_data_consistency()
        print("\nData Consistency:")
        if consistency["is_consistent"]:
            print("  ✓ All data is consistent")
        else:
            print("  ✗ Issues found:")
            for issue in consistency["issues"]:
                print(f"    - {issue}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="B站 RAG 项目测试工具")
    parser.add_argument(
        "--mode",
        choices=["endpoint", "concurrent", "load", "database"],
        default="endpoint",
        help="测试模式",
    )
    parser.add_argument("--endpoint", default="/health", help="测试端点")
    parser.add_argument("--method", default="GET", help="HTTP 方法")
    parser.add_argument("--count", type=int, default=10, help="并发请求数")
    parser.add_argument("--duration", type=int, default=60, help="负载测试持续时间（秒）")
    parser.add_argument("--concurrent", type=int, default=5, help="并发连接数")

    args = parser.parse_args()

    if args.mode == "endpoint":
        runner = TestRunner()
        result = runner.test_endpoint(args.method, args.endpoint)
        runner.print_results([result])

    elif args.mode == "concurrent":
        runner = TestRunner()
        results = runner.concurrent_test(args.method, args.endpoint, args.count)
        runner.print_results(results)

    elif args.mode == "load":
        runner = TestRunner()
        result = runner.load_test(args.duration, args.concurrent)
        print("\n" + "=" * 80)
        print("Load Test Results")
        print("=" * 80)
        for key, value in result.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.3f}")
            else:
                print(f"  {key}: {value}")

    elif args.mode == "database":
        validator = DatabaseValidator()
        validator.print_statistics()


if __name__ == "__main__":
    main()
