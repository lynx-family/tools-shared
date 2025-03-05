# Commit Message Format
We use a fixed format for commit message checks. Please refer to the commit message template below for details:
```
[Label] Title of the commit message (one line)

Summary of change:
Longer description of change addressing as appropriate: why the change
is made, context if it is part of many changes, description of previous
behavior and newly introduced differences, etc.

Long lines should be wrapped to 72 columns for easier log message
viewing in terminals.

issue: #xxx
doc: https://xxxxxxxx
TEST: Test cases
```
Some parts in the message template are required, while others are optional. We use the labels `[Required]` and `[Optional]` to differentiate them in the detailed explanation below:
- **[Required]** The first line of the commit message should be the title, summarizing the changes (the title must be on a separate line).
- **[Required]** The title must start with at least one label, and the first label must be one of the following: `Feature`, `BugFix`, `Refactor`, `Optimize`, `Infra`, `Testing`, `Doc`. The format should be: `[Label]`, e.g., `[BugFix]`, `[Feature]`, `[BugFix][Tools]` (there must be at least one space between the label(s) and the title content, and the title must not be empty).
    >
    > Which label should I use? Here are the explanations for them:
    > - **`[Feature]`**: New features, new functions, or changes to existing features and functions. For example:
    >   - `[Feature] Add new API for data binding` Add a new API for data binding
    >   - `[Feature] Add service for light sensors` Add a service for light sensors
    >   - `[Feature][Log] Support async event report` Support asynchronous event reporting
    > - **`[BugFix]`**: Fixes for functional defects, performance anomalies, and problems in developer tools, etc. For example:
    >   - `[BugFix] Fix exception when playing audio` Fix the exception when playing audio
    >   - `[BugFix] Fix leaks in xxx` Fix the memory leak problem in xxx
    >   - `[BugFix][DevTool] Fix data error in DevTool` Fix the data error in the debug tool
    > - **`[Refactor]`**: The overall refactoring of a module or function (mainly refers to large-scale code rewriting or architecture optimization; small-scale refactoring can be classified as Optimize). For example:
    >   - `[Refactor][Memory] Memory management in xxxx` Refactor the memory management of the xxx module
    >   - `[Refactor][TestBench] XX module in TestBench` Refactor the xxx module in the TestBench
    > - **`[Optimize]`**: Small-scale optimization of a certain feature or indicator, such as performance optimization, memory optimization, etc. For example:
    >   - `[Optimize][Performance] Jank when scrolling in xxxx` Optimization of the smoothness when scrolling in xxxx
    > - **`[Infra]`**: Changes related to the compilation framework, CQ configuration, basic tools, etc. For example:
    >   - `[Infra][Compile] Use -Oz compile params in xxx` Use -Oz compilation parameters
    > - **`[Testing]`**: Modifications related to test cases and test frameworks. For example:
    >   - `[Testing][Android] Fix xxx test case for Android` Fix a test case for Android
    >   - `[Testing] Optimize test process` Optimize the process of a certain test framework
    >
    > Modifications only involving test cases, even if it is a `BugFix`, should be classified as `Testing`.
    > If both `Feature` code and related test cases are submitted in the same patch, it should be classified as `Feature`.
- **[Required]** The section following the title should be the summary, providing a detailed description of the changes (there must be a blank line between the title and the summary).
- **[Optional]** The commit can be linked to an issue, and the issue ID needs to appear in the format `issue: #xxx`.
- **[Optional]** The commit can be linked to a document. If you labeled your changes as `Feature` or `Refactor`, this is required. The format of a doc link should be like this: `doc: https://xxxxxxx`
- **[Optional]** The commit can be linked to tests (unit tests, UI tests). You can write the case names in the format: `TEST: test_case_1, test_case_2`