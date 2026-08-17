"""
================================================================================
Mini NPU Simulator & Tensor Pattern Classifier
================================================================================
Architecture: Object-Oriented Domain Driven Architecture
Computation : Hardware-inspired Frobenius Inner Product & Flat Vector Dot MAC
Author      : Engineering Team (Refactored Pipeline Edition)
================================================================================
"""

from dataclasses import dataclass, field
from enum import Enum
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


# ============================================================================
# 1. Domain Constants & Runtime Configuration
# ============================================================================

class TargetClass(str, Enum):
    """Normalized classification target labels."""
    CROSS = "Cross"
    X = "X"
    UNCERTAIN = "UNDECIDED"


@dataclass(frozen=True)
class RuntimeConfig:
    """Central configuration for precision tolerances and profiler settings."""
    FLOAT_TOLERANCE: float = 1e-9
    PROFILER_WARMUP: int = 1
    PROFILER_REPETITIONS: int = 10
    STANDARD_BENCHMARK_DIMS: Tuple[int, ...] = (3, 5, 13, 25)
    CONSOLE_BAR_LENGTH: int = 46


CONFIG = RuntimeConfig()


# ============================================================================
# 2. Custom Exceptions for Explicit Error Handling
# ============================================================================

class MatrixValidationError(ValueError):
    """Raised when 2D array dimensions or numeric types violate constraints."""
    pass


class DatasetSchemaError(KeyError):
    """Raised when JSON dataset structure is invalid or missing required keys."""
    pass


# ============================================================================
# 3. Core Mathematical Tensor / Matrix Abstraction
# ============================================================================

class Matrix2D:
    """
    Encapsulates a square 2-dimensional real-valued matrix.
    Supports 2D coordinate indexing and flat memory buffer representation.
    """

    def __init__(self, dimension: int, initial_val: float = 0.0) -> None:
        if dimension <= 0:
            raise MatrixValidationError(f"Dimension must be positive, got {dimension}")
        self._dim: int = dimension
        self._buffer: List[List[float]] = [
            [float(initial_val)] * dimension for _ in range(dimension)
        ]

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def shape(self) -> Tuple[int, int]:
        return (self._dim, self._dim)

    @property
    def cells(self) -> List[List[float]]:
        return self._buffer

    def read(self, row: int, col: int) -> float:
        return self._buffer[row][col]

    def write(self, row: int, col: int, value: Union[int, float]) -> None:
        self._buffer[row][col] = float(value)

    def to_flat_vector(self) -> List[float]:
        """Flattens 2D matrix into a contiguous 1D array of length N^2."""
        return [elem for row in self._buffer for elem in row]

    @classmethod
    def from_nested_list(cls, data: Sequence[Sequence[Any]]) -> "Matrix2D":
        """
        Constructs and validates a square matrix from nested sequences.
        Validates squareness and numeric integrity.
        """
        if not isinstance(data, (list, tuple)) or len(data) == 0:
            raise MatrixValidationError("Input must be a non-empty 2D sequence.")

        dim = len(data)
        instance = cls(dim)

        for r_idx, row in enumerate(data):
            if not isinstance(row, (list, tuple)) or len(row) != dim:
                row_len = len(row) if isinstance(row, (list, tuple)) else type(row).__name__
                raise MatrixValidationError(
                    f"Square matrix violation: expected {dim} items, row {r_idx + 1} has {row_len}"
                )

            for c_idx, cell in enumerate(row):
                if isinstance(cell, bool) or not isinstance(cell, (int, float)):
                    raise MatrixValidationError(
                        f"Non-numeric scalar at row {r_idx + 1}, col {c_idx + 1}: {cell!r}"
                    )
                instance.write(r_idx, c_idx, cell)

        return instance


# ============================================================================
# 4. Multiply-Accumulate (MAC) Arithmetic Engine
# ============================================================================

class MacArithmeticUnit:
    """Hardware-inspired Multiply-Accumulate (MAC) computation core."""

    @staticmethod
    def execute_2d(matrix_a: Matrix2D, matrix_b: Matrix2D) -> float:
        """
        Calculates Frobenius inner product: sum_{i,j} (A_{i,j} * B_{i,j}).
        Complexity: exactly N^2 multiplication operations + N^2 additions.
        """
        if matrix_a.dimension != matrix_b.dimension:
            raise MatrixValidationError(
                f"Dimension mismatch for 2D MAC: {matrix_a.dimension} vs {matrix_b.dimension}"
            )

        accum: float = 0.0
        n = matrix_a.dimension
        buf_a = matrix_a.cells
        buf_b = matrix_b.cells

        for r in range(n):
            row_a = buf_a[r]
            row_b = buf_b[r]
            for c in range(n):
                accum += row_a[c] * row_b[c]

        return accum

    @staticmethod
    def execute_1d_flat(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
        """Computes dot product over flattened 1D continuous buffers."""
        if len(vec_a) != len(vec_b):
            raise MatrixValidationError(f"Vector length mismatch: {len(vec_a)} vs {len(vec_b)}")

        accum: float = 0.0
        for i in range(len(vec_a)):
            accum += vec_a[i] * vec_b[i]
        return accum


# ============================================================================
# 5. Synthetic Pattern & Filter Synthesizer
# ============================================================================

class PatternSynthesizer:
    """Generates canonical geometric filter kernels for pattern recognition."""

    @staticmethod
    def build_cross(n: int) -> Matrix2D:
        """
        Generates N×N orthogonal cross '+' filter with central horizontal and vertical bars = 1.0.
        """
        mat = Matrix2D(n, 0.0)
        mid = n // 2
        for idx in range(n):
            mat.write(mid, idx, 1.0)
            mat.write(idx, mid, 1.0)
        return mat

    @staticmethod
    def build_diagonal_x(n: int) -> Matrix2D:
        """
        Generates N×N diagonal 'X' filter with primary and secondary diagonals = 1.0.
        """
        mat = Matrix2D(n, 0.0)
        for idx in range(n):
            mat.write(idx, idx, 1.0)
            mat.write(idx, n - 1 - idx, 1.0)
        return mat


# ============================================================================
# 6. Label Normalization & Inference Engine
# ============================================================================

class LabelNormalizer:
    """Converts diverse external token representations into standardized labels."""

    @classmethod
    def standardize(cls, raw: Any) -> Optional[TargetClass]:
        if not isinstance(raw, str):
            return None
        cleaned = raw.strip().lower()
        if cleaned in ("+", "cross"):
            return TargetClass.CROSS
        if cleaned in ("x",):
            return TargetClass.X
        return None


class InferenceEngine:
    """Performs hypothesis testing and boundary classification with epsilon tolerance."""

    @staticmethod
    def classify_binary(score_cross: float, score_x: float, tol: float = CONFIG.FLOAT_TOLERANCE) -> TargetClass:
        delta = abs(score_cross - score_x)
        if delta < tol:
            return TargetClass.UNCERTAIN
        return TargetClass.CROSS if score_cross > score_x else TargetClass.X

    @staticmethod
    def compare_ab(score_a: float, score_b: float, tol: float = CONFIG.FLOAT_TOLERANCE) -> str:
        delta = abs(score_a - score_b)
        if delta < tol:
            return TargetClass.UNCERTAIN.value
        return "A" if score_a > score_b else "B"


# ============================================================================
# 7. Performance Profiler & Benchmark
# ============================================================================

@dataclass
class BenchmarkRecord:
    dim: int
    avg_2d_ms: float
    total_ops: int
    avg_1d_ms: float


class PerformanceProfiler:
    """High-precision latency profiling tool for MAC kernels."""

    @staticmethod
    def profile_kernel(func, arg1, arg2, repeats: int = CONFIG.PROFILER_REPETITIONS) -> float:
        # Warmup iteration
        func(arg1, arg2)

        cumulative_sec = 0.0
        for _ in range(repeats):
            t_start = time.perf_counter()
            func(arg1, arg2)
            cumulative_sec += time.perf_counter() - t_start

        return (cumulative_sec / repeats) * 1000.0

    @classmethod
    def evaluate_dimensions(cls, dimensions: Sequence[int] = CONFIG.STANDARD_BENCHMARK_DIMS) -> List[BenchmarkRecord]:
        records = []
        for dim in dimensions:
            pat = PatternSynthesizer.build_diagonal_x(dim)
            flt = PatternSynthesizer.build_cross(dim)

            lat_2d = cls.profile_kernel(MacArithmeticUnit.execute_2d, pat, flt)
            lat_1d = cls.profile_kernel(
                MacArithmeticUnit.execute_1d_flat,
                pat.to_flat_vector(),
                flt.to_flat_vector()
            )

            records.append(
                BenchmarkRecord(
                    dim=dim,
                    avg_2d_ms=lat_2d,
                    total_ops=dim * dim,
                    avg_1d_ms=lat_1d
                )
            )
        return records


# ============================================================================
# 8. Batch Dataset Evaluation Driver
# ============================================================================

@dataclass
class TestCaseResult:
    case_id: str
    passed: bool
    verdict: TargetClass
    expected: TargetClass
    score_cross: float
    score_x: float
    failure_reason: str = ""
    log_messages: List[str] = field(default_factory=list)


class BatchDatasetEvaluator:
    """Manages loading, parsing, and verifying test suites from JSON files."""

    def __init__(self, json_source: str) -> None:
        self.source_path = json_source
        self.filter_bank: Dict[str, Dict[TargetClass, Matrix2D]] = {}
        self.raw_patterns: Dict[str, Any] = {}

    def load_and_prepare(self) -> bool:
        if not os.path.isfile(self.source_path):
            print(f"✗ File not found: {self.source_path}")
            return False

        try:
            with open(self.source_path, "r", encoding="utf-8") as stream:
                payload = json.load(stream)
        except Exception as exc:
            print(f"✗ Failed to parse JSON: {exc}")
            return False

        raw_filters = payload.get("filters")
        self.raw_patterns = payload.get("patterns", {})

        if not isinstance(raw_filters, dict) or not isinstance(self.raw_patterns, dict):
            print("✗ Invalid schema: root must contain 'filters' and 'patterns' dictionaries.")
            return False

        self._parse_filters(raw_filters)
        return bool(self.filter_bank)

    def _parse_filters(self, raw_filters: Dict[str, Any]) -> None:
        for size_key in sorted(raw_filters.keys(), key=lambda k: (len(k), k)):
            node = raw_filters[size_key]
            if not isinstance(node, dict):
                print(f"✗ Filter group '{size_key}' is not an object.")
                continue

            parsed_group: Dict[TargetClass, Matrix2D] = {}
            for raw_lbl, matrix_data in node.items():
                std_lbl = LabelNormalizer.standardize(raw_lbl)
                if std_lbl is None:
                    print(f"✗ Unrecognized filter label: {raw_lbl!r}")
                    continue
                try:
                    parsed_group[std_lbl] = Matrix2D.from_nested_list(matrix_data)
                except MatrixValidationError as err:
                    print(f"✗ Error in filter {size_key}/{raw_lbl}: {err}")

            if TargetClass.CROSS in parsed_group and TargetClass.X in parsed_group:
                self.filter_bank[size_key] = parsed_group
                print(f"✓ [{size_key:<8}] Filter kernel loaded successfully (Cross, X)")
            else:
                print(f"✗ [{size_key}] Incomplete filter set: missing Cross or X kernel.")

    def run_evaluations(self) -> List[TestCaseResult]:
        outcomes: List[TestCaseResult] = []

        for case_id, entry in self.raw_patterns.items():
            result = self._evaluate_single_case(case_id, entry)
            outcomes.append(result)

        return outcomes

    def _evaluate_single_case(self, case_id: str, entry: Any) -> TestCaseResult:
        res = TestCaseResult(
            case_id=case_id,
            passed=False,
            verdict=TargetClass.UNCERTAIN,
            expected=TargetClass.UNCERTAIN,
            score_cross=0.0,
            score_x=0.0
        )

        if not isinstance(entry, dict) or "input" not in entry or "expected" not in entry:
            res.failure_reason = "Malformed case entry: missing 'input' or 'expected'"
            return res

        parts = case_id.split("_")
        if len(parts) < 2 or parts[0] != "size":
            res.failure_reason = f"Invalid case_id key format: '{case_id}'"
            return res

        try:
            dim_val = int(parts[1])
        except ValueError:
            res.failure_reason = f"Non-integer dimension in key: '{case_id}'"
            return res

        size_key = f"size_{dim_val}"
        if size_key not in self.filter_bank:
            res.failure_reason = f"No filter kernels registered for dimension {dim_val}"
            return res

        try:
            input_matrix = Matrix2D.from_nested_list(entry["input"])
        except MatrixValidationError as err:
            res.failure_reason = f"Input pattern parse error: {err}"
            return res

        if input_matrix.dimension != dim_val:
            res.failure_reason = f"Dimension mismatch: expected {dim_val}x{dim_val}, got {input_matrix.dimension}x{input_matrix.dimension}"
            return res

        expected_lbl = LabelNormalizer.standardize(entry["expected"])
        if expected_lbl is None:
            res.failure_reason = f"Unknown ground truth label: {entry['expected']!r}"
            return res
        res.expected = expected_lbl

        cross_flt = self.filter_bank[size_key][TargetClass.CROSS]
        x_flt = self.filter_bank[size_key][TargetClass.X]

        res.score_cross = MacArithmeticUnit.execute_2d(input_matrix, cross_flt)
        res.score_x = MacArithmeticUnit.execute_2d(input_matrix, x_flt)
        res.verdict = InferenceEngine.classify_binary(res.score_cross, res.score_x)

        res.log_messages.append(f"  Cross Score: {res.score_cross:<10.4f} | X Score: {res.score_x:<10.4f}")

        if res.verdict == res.expected:
            res.passed = True
            res.log_messages.append(f"  Prediction: {res.verdict.value:<5} | Target: {res.expected.value:<5} => [PASS]")
        elif res.verdict == TargetClass.UNCERTAIN:
            diff = abs(res.score_cross - res.score_x)
            res.failure_reason = f"Tie condition triggered (|Δ|={diff:.3e} < {CONFIG.FLOAT_TOLERANCE})"
            res.log_messages.append(f"  Prediction: {res.verdict.value:<5} | Target: {res.expected.value:<5} => [FAIL: Tie Rule]")
        else:
            res.failure_reason = f"Prediction ({res.verdict.value}) != Ground Truth ({res.expected.value})"
            res.log_messages.append(f"  Prediction: {res.verdict.value:<5} | Target: {res.expected.value:<5} => [FAIL: Misclassification]")

        return res


# ============================================================================
# 9. Console UI & Interactive Controllers
# ============================================================================

class ConsoleIO:
    """Handles formatted text I/O and user interaction with validation."""

    @staticmethod
    def prompt(msg: str = "") -> str:
        try:
            return input(msg)
        except (EOFError, KeyboardInterrupt):
            print("\n\nSession terminated by user.")
            sys.exit(0)

    @staticmethod
    def print_section(title: str) -> None:
        div = "=" * CONFIG.CONSOLE_BAR_LENGTH
        print(f"\n{div}\n  {title}\n{div}")

    @staticmethod
    def display_matrix(matrix: Matrix2D, label: str) -> None:
        print(f"✓ {label} ({matrix.dimension}×{matrix.dimension}):")
        for r in range(matrix.dimension):
            row_repr = " ".join(f"{matrix.read(r, c):>5.1f}" for c in range(matrix.dimension))
            print(f"  [ {row_repr} ]")

    @classmethod
    def capture_matrix(cls, dim: int, prompt_title: str) -> Matrix2D:
        print(f"\nEntering {prompt_title} ({dim} rows, space-delimited floats per row):")
        matrix = Matrix2D(dim)
        row_idx = 0
        while row_idx < dim:
            line_str = cls.prompt(f"  Row {row_idx + 1}/{dim}> ").strip()
            tokens = line_str.split()
            if len(tokens) != dim:
                print(f"  [Error] Expected {dim} values, received {len(tokens)}. Re-enter row {row_idx + 1}.")
                continue
            try:
                numeric_vals = [float(item) for item in tokens]
            except ValueError:
                print(f"  [Error] Contains invalid float token. Re-enter row {row_idx + 1}.")
                continue

            for col_idx, val in enumerate(numeric_vals):
                matrix.write(row_idx, col_idx, val)
            row_idx += 1
        return matrix

    @staticmethod
    def render_benchmark_table(records: Sequence[BenchmarkRecord]) -> None:
        header = f"{'Dimension':<12}{'2D Avg (ms)':>14}{'Operations (N²)':>16}{'1D Avg (ms)':>14}{'Advantage':>12}"
        print(header)
        print("-" * len(header))
        for rec in records:
            advantage = "1D Flat" if rec.avg_1d_ms < rec.avg_2d_ms else "2D Loop"
            print(
                f"{f'{rec.dim}×{rec.dim}':<12}"
                f"{rec.avg_2d_ms:>14.4f}"
                f"{rec.total_ops:>16}"
                f"{rec.avg_1d_ms:>14.4f}"
                f"{advantage:>12}"
            )


# ============================================================================
# 10. Application Entry Point & Dispatcher
# ============================================================================

class NpuClassifierApplication:
    """Master workflow controller for the NPU pattern classification suite."""

    def __init__(self, default_dataset: str = "data.json") -> None:
        self.default_dataset = default_dataset

    def run_manual_pipeline(self) -> None:
        ConsoleIO.print_section("Interactive 3×3 Dual Filter Classifier")

        filter_a = ConsoleIO.capture_matrix(3, "Reference Kernel A")
        ConsoleIO.display_matrix(filter_a, "Kernel A")

        filter_b = ConsoleIO.capture_matrix(3, "Reference Kernel B")
        ConsoleIO.display_matrix(filter_b, "Kernel B")

        input_pattern = ConsoleIO.capture_matrix(3, "Test Input Pattern")
        ConsoleIO.display_matrix(input_pattern, "Input Pattern")

        ConsoleIO.print_section("MAC Similarity Computation")
        score_a = MacArithmeticUnit.execute_2d(input_pattern, filter_a)
        score_b = MacArithmeticUnit.execute_2d(input_pattern, filter_b)

        lat_a = PerformanceProfiler.profile_kernel(MacArithmeticUnit.execute_2d, input_pattern, filter_a)
        lat_b = PerformanceProfiler.profile_kernel(MacArithmeticUnit.execute_2d, input_pattern, filter_b)
        mean_lat = (lat_a + lat_b) / 2.0

        print(f"• Similarity with Kernel A (MAC Score): {score_a:.6f}")
        print(f"• Similarity with Kernel B (MAC Score): {score_b:.6f}")
        print(f"• Mean Execution Latency ({CONFIG.PROFILER_REPETITIONS} runs): {mean_lat:.4f} ms")

        verdict = InferenceEngine.compare_ab(score_a, score_b)
        if verdict == TargetClass.UNCERTAIN.value:
            print("• Classification Result: Inconclusive (|Score A - Score B| < Epsilon)")
        else:
            winner = "Kernel A" if verdict == "A" else "Kernel B"
            print(f"• Classification Result: Pattern matches {winner} (Selected: {verdict})")

        ConsoleIO.print_section(f"3×3 Kernel Benchmark ({CONFIG.PROFILER_REPETITIONS} iterations)")
        recs = PerformanceProfiler.evaluate_dimensions((3,))
        ConsoleIO.render_benchmark_table(recs)

        ConsoleIO.prompt("\nPress Enter to return to primary menu...")

    def run_dataset_pipeline(self, target_path: Optional[str] = None) -> None:
        dataset_path = target_path or self.default_dataset
        ConsoleIO.print_section(f"Batch Dataset Evaluation: {dataset_path}")

        evaluator = BatchDatasetEvaluator(dataset_path)
        if not evaluator.load_and_prepare():
            ConsoleIO.prompt("\nEvaluation aborted. Press Enter to continue...")
            return

        ConsoleIO.print_section("Executing Pattern Test Cases")
        results = evaluator.run_evaluations()

        for res in results:
            print(f"\n[Case: {res.case_id}]")
            for msg in res.log_messages:
                print(msg)
            if not res.passed and not res.log_messages:
                print(f"  [FAIL] {res.failure_reason}")

        ConsoleIO.print_section("Summary Performance & Accuracy Report")
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed_cases = [r for r in results if not r.passed]
        acc_pct = (passed / total * 100.0) if total > 0 else 0.0

        print(f"• Total Evaluations : {total}")
        print(f"• Successful (PASS) : {passed}")
        print(f"• Unsuccessful (FAIL): {len(failed_cases)}")
        print(f"• Test Accuracy     : {acc_pct:.1f}%")

        if failed_cases:
            print("\nBreakdown of Unsuccessful Cases:")
            for f in failed_cases:
                print(f"  - {f.case_id}: {f.failure_reason}")

        ConsoleIO.print_section(f"Multi-Scale Latency Benchmark (Repetitions={CONFIG.PROFILER_REPETITIONS})")
        recs = PerformanceProfiler.evaluate_dimensions(CONFIG.STANDARD_BENCHMARK_DIMS)
        ConsoleIO.render_benchmark_table(recs)

        ConsoleIO.prompt("\nPress Enter to return to primary menu...")

    def run_synthetic_demo(self) -> None:
        ConsoleIO.print_section("Synthetic Pattern & Kernel Demonstration")
        while True:
            raw = ConsoleIO.prompt("Enter matrix dimension N (odd integer >= 3): ").strip()
            try:
                n = int(raw)
                if n < 3:
                    print("Dimension must be at least 3.")
                    continue
                break
            except ValueError:
                print("Invalid integer. Please try again.")

        cross_k = PatternSynthesizer.build_cross(n)
        diag_k = PatternSynthesizer.build_diagonal_x(n)

        ConsoleIO.display_matrix(cross_k, f"Canonical {n}×{n} Cross (+) Filter")
        print()
        ConsoleIO.display_matrix(diag_k, f"Canonical {n}×{n} Diagonal (X) Filter")

        score_cross_with_x = MacArithmeticUnit.execute_2d(diag_k, cross_k)
        score_x_with_x = MacArithmeticUnit.execute_2d(diag_k, diag_k)
        decision = InferenceEngine.classify_binary(score_cross_with_x, score_x_with_x)

        print(f"\nVerification Metric when input is X-Pattern:")
        print(f"  Score vs Cross Filter: {score_cross_with_x:.4f}")
        print(f"  Score vs X Filter    : {score_x_with_x:.4f}")
        print(f"  Classifier Decision  : {decision.value} (Expected: X)")

        ConsoleIO.prompt("\nPress Enter to return to primary menu...")

    def run_master_loop(self) -> None:
        while True:
            print("\n" + "=" * 50)
            print("      NPU MAC PATTERN CLASSIFIER STUDIO      ")
            print("=" * 50)
            print("  [1] Interactive 3×3 Mode (Kernel A vs B)")
            print("  [2] Batch JSON Evaluation (Cross vs X)")
            print("  [3] Synthetic Kernel Synthesizer Demo")
            print("  [4] Multi-Dimension Performance Profiler")
            print("  [0] Exit Application")
            print("=" * 50)

            choice = ConsoleIO.prompt("Select execution mode [0-4]: ").strip()

            if choice in ("0", "q", "exit"):
                print("\nExiting NPU Studio. Goodbye!\n")
                break
            elif choice == "1":
                self.run_manual_pipeline()
            elif choice == "2":
                custom = ConsoleIO.prompt(f"Dataset path (default: {self.default_dataset}): ").strip()
                path = custom if custom else self.default_dataset
                self.run_dataset_pipeline(path)
            elif choice == "3":
                self.run_synthetic_demo()
            elif choice == "4":
                ConsoleIO.print_section("Hardware Scalability Latency Profiler")
                recs = PerformanceProfiler.evaluate_dimensions(CONFIG.STANDARD_BENCHMARK_DIMS)
                ConsoleIO.render_benchmark_table(recs)
                ConsoleIO.prompt("\nPress Enter to return to primary menu...")
            else:
                print("Invalid selection. Enter a number between 0 and 4.")


def main() -> None:
    dataset_target = sys.argv[1] if len(sys.argv) > 1 else "data.json"
    app = NpuClassifierApplication(default_dataset=dataset_target)
    app.run_master_loop()


if __name__ == "__main__":
    main()