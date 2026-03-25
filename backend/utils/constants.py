# backend/utils/constants.py

# Complexity thresholds (Cyclomatic Complexity)
COMPLEXITY_LOW = 5
COMPLEXITY_MEDIUM = 10
COMPLEXITY_HIGH = 20
COMPLEXITY_VERY_HIGH = 30

# Decay risk levels
RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"
RISK_CRITICAL = "critical"

# File extensions to analyze
SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".cpp", ".c", ".go", ".rs",
    ".php", ".rb", ".swift", ".kt"
}

# Metrics
METRICS = {
    "cyclomatic_complexity": "Cyclomatic Complexity",
    "lines_of_code": "Lines of Code",
    "maintainability_index": "Maintainability Index",
    "change_frequency": "Change Frequency",
    "bug_density": "Bug Density",
    "dependency_count": "Dependency Count"
}
