---
name: create-doc
description: Create documentation in English with Korean translation
argument-hint: "feature name - e.g., screener, backtesting, portfolio"
allowed-tools: Read, Write, Glob, Grep, Bash
---

# Documentation Creation Workflow

Create documentation for `$ARGUMENTS`.

## Workflow

1. **Analyze**: Understand the feature/module to document
2. **Write English doc**: Create `docs/{FEATURE}_README.md`
3. **Translate to Korean**: Create `docs/ko/{FEATURE}_README.md`
4. **Update references**: Add links to CLAUDE.md or README.md

## Documentation Structure

### English (`docs/{FEATURE}_README.md`)

```markdown
# Feature Name

Brief description of what this feature does.

## Quick Start

\`\`\`python
# Minimal working example
\`\`\`

## Installation / Setup

(If needed)

## Usage

### Basic Usage

### Advanced Usage

## API Reference

| Class/Function | Description | Parameters |
|----------------|-------------|------------|
| `ClassName` | What it does | `param1`, `param2` |

## Configuration

(If applicable)

## Examples

### Example 1: Basic

### Example 2: Advanced

## File Structure

\`\`\`
module/
├── file1.py    # Description
└── file2.py    # Description
\`\`\`

## Related

- [Link to related doc](./OTHER_README.md)
```

### Korean (`docs/ko/{FEATURE}_README.md`)

- Translate all content to Korean
- Keep code examples in English
- Keep file paths, class names, function names in English
- Add "이 문서는 [영문 버전](../FEATURE_README.md)의 번역입니다." at the top

## Writing Guidelines

### Language
- **English doc**: Natural, technical English
- **Korean doc**: Professional Korean (존댓말)
- **Code comments**: Keep original language

### Style
- Use tables for API references
- Use code blocks with language hints
- Keep examples minimal but complete
- Link to related documentation

### Structure
- Start with Quick Start (working example)
- Put API reference after usage examples
- End with file structure and related links

## Output

1. Create English documentation at `docs/{FEATURE}_README.md`
2. Create Korean documentation at `docs/ko/{FEATURE}_README.md`
3. Report both file paths to user
4. Suggest adding links to CLAUDE.md if needed
