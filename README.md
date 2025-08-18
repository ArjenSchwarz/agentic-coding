# Agentic Coding process

This repository contains my current process for working with agentic coding assistants. It's focused around spec-driven development and has a number of helpful tools and commands. Feel free to use what you see here and/or propose improvements.

## Commands

The framework includes commands for a complete feature development workflow (detailed in [spec-workflow](spec-workflow.md)):

- **`requirements`** - Generate and refine feature requirements in EARS format
- **`design`** - Create comprehensive design documents based on approved requirements
- **`tasks`** - Convert designs into actionable implementation task lists
- **`next-task`** - Execute the next group of tasks from the implementation plan
- **`commits`** - Format, stage, and commit changes with proper changelog management

## Agents

The framework provides specialized AI agents for different aspects of development. These are defined for use in Claude Code, and not every tool supports sub-agents like this. So there may be some requirements here that don't work well in other tools, or have other dependencies like peer-review-validator that requires Gemini CLI to be installed and configured.

- **`code-simplifier`** - Reviews code for complexity reduction and maintainability improvements
- **`design-critic`** - Provides critical review of design documents and architecture proposals
- **`efficiency-optimizer`** - Analyzes code for performance optimization opportunities
- **`peer-review-validator`** - Validates decisions by consulting with external AI systems
- **`research-agent`** - Conducts comprehensive research and generates structured reports
- **`ui-ux-reviewer`** - Evaluates user interfaces for usability and accessibility improvements

## Workflow

1. Start with `requirements` to define what needs to be built
2. Use `design` to plan the architecture and approach
3. Generate implementation steps with `tasks`
4. Execute incrementally using `next-task`
5. Commit progress using `commits`

Each phase requires explicit user approval before proceeding to ensure quality and alignment.

## File Structure

Feature work is organized in `agents/{feature_name}/` directories containing:
- `requirements.md` - Feature requirements in EARS format
- `design.md` - Comprehensive design document
- `tasks.md` - Implementation task checklist
- `decision_log.md` - Decisions and rationales

This framework is designed to work with various AI coding tools including Claude Code, GitHub Copilot, and Cline.