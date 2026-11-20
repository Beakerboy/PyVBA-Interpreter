[![Python package](https://github.com/Beakerboy/PyVBA-Interpreter/actions/workflows/python-package.yml/badge.svg)](https://github.com/Beakerboy/PyVBA-Interpreter/actions/workflows/python-package.yml)
[![Coverage Status](https://coveralls.io/repos/github/Beakerboy/PyVBA-Interpreter/badge.svg?branch=dev)](https://coveralls.io/github/Beakerboy/PyVBA-Interpreter?branch=dev)

# PyVBA-Interpreter

A Python-based VBA interpreter built with ANTLR4. This tool allows you to execute VBA code directly from your terminal, supporting complex logic, recursive function calls, and robust expression evaluation.

## Features

-   **Expression Engine**: Full support for algebraic, relational, and Boolean expressions.
-   **Function Support**: Call functions and receive return values.
-   **Recursion**: Supports recursive logic (e.g., calculating factorials).
-   **Memory Management**: Efficiently reads and saves variables to the call stack.
-   **Type Safety**: Fully type-hinted and verified with **MyPy**.
-   **CLI**: Simple command-line interface for executing `.bas` files.
-   **Tested**: Includes a comprehensive test suite powered by **pytest**.

## Installation

Since the project is not currently on PyPI, clone the repository and install the dependencies locally:

```bash
git clone https://github.com/Beakerboy/PyVBA-Interpreter.git
cd PyVBA-Interpreter
pip install -e .[tests]
```

## Usage

You can run a specific function within a VBA module using the CLI:

```bash
pyvba_interpreter <function_name> <file_path>
```

### Example
If you have a file named `module.bas` with a `main` function:
```bash
pyvba_interpreter main module.bas
```

## Development & Contributing

**PyVBA-Interpreter is currently under active development.** 

While the core engine supports expressions, recursion, and stack management, many VBA features are still missing or incomplete. We welcome contributions from the community to help expand its capabilities!

### Contribution Guidelines
If you'd like to contribute, please keep the following in mind:
- **Pull Requests**: We encourage PRs for new features or bug fixes. Please ensure your code:
    - Follows **PEP8** style guidelines.
    - Passes static type checking via **MyPy**.
    - Includes **pytest** coverage for any new logic or edge cases.
- **Bug Reports**: When opening an issue, please provide as much detail as possible to help us reproduce it, including:
    - The specific VBA snippet causing the error.
    - The expected output vs. the actual output.
    - Your Python version and any relevant environment details.

### Local Quality Checks
Before submitting a PR, please run our local verification suite:

```bash
# Run the test suite
pytest

# Check for type safety
mypy .

# Check for PEP8 compliance
flake8 .
```

## Current Roadmap

We are working toward full compliance with the [VBA Language Specification](https://learn.microsoft.com/en-us/openspecs/microsoft_general_purpose_programming_languages/ms-vbal/d5418146-0bd2-45eb-9c7a-fd9502722c74). Future updates will focus on:

-   **Control Structures** Currently no control structures have been implemented. Priority is `If/Then/Else`.
-   **Arrays**: Support for fixed and dynamic arrays, including `Dim`, `ReDim`, and `Preserve` statements.
-   **Error Handling**: Implementation of [On Error GoTo](https://learn.microsoft.com/en-us/office/vba/language/reference/user-interface-help/on-error-statement) and [On Error Resume Next](https://stackoverflow.com/questions/29390673/error-handling-in-vba-on-error-resume-next) logic.
-   **Object Support**: Support for custom **Class Modules**, properties (`Property Get/Let/Set`), and early/late binding.
-   **Core Library**: Expanding intrinsic [VBA functions](https://learn.microsoft.com/en-us/office/vba/language/reference/user-interface-help/visual-basic-language-reference) for string manipulation, math, and date handling.


## How it Works
The interpreter uses **ANTLR4** to parse VBA syntax into an Abstract Syntax Tree (AST). The Python backend then traverses the tree, managing a call stack to handle variable scoping and function execution.

## Differences from MS-VBA
* While...Loop triggers a parsing error instead of a compile error
