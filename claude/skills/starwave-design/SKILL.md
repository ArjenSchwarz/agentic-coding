---
name: starwave:design
description: 2. Create Feature Design Document
---

### 2. Create Feature Design Document

After the user approves the Requirements, develop a design document based on the feature requirements, conducting necessary research during the design process.
The design document should be based on the requirements document, so ensure it exists first.

**Writing Style — Signal over Volume:**

The design exists to make implementation decisions clear and capture non-obvious thinking. It is not a brochure, a tutorial, or a restatement of the requirements. Favor brevity and substance.

- The model MUST keep the design to the minimum length needed to convey the decisions. If a section can be expressed in two sentences, it MUST NOT be padded to a paragraph.
- The model MUST NOT restate or paraphrase the requirements document. Reference requirements by ID when needed; do not duplicate them.
- The model MUST NOT include filler content such as motivational preambles, generic benefits ("improves maintainability", "enhances user experience"), or summaries that repeat the preceding section.
- The model MUST NOT describe what is obvious from the code, type signatures, or standard library conventions. Document the non-obvious: constraints, trade-offs, invariants, and decisions that could reasonably have gone another way.
- The model MUST OMIT any of the required sections that do not apply to the feature rather than filling them with boilerplate (e.g., a pure refactor may have no new data models; a CLI tweak may have no error-handling considerations). When omitting a section, the model MUST NOT leave a placeholder — just leave the section out.
- The model MUST NOT use hyperbolic or marketing language ("robust", "comprehensive", "seamless", "powerful", "cutting-edge").
- Prose SHOULD be replaced with tables, lists, or short type/interface sketches whenever those convey the same information more densely.
- Diagrams SHOULD only be included when they reveal structure that prose cannot convey concisely. Do not add a diagram for its own sake.
- Research findings MUST be distilled into the decisions they informed. Do not dump raw research into the design.

**Constraints:**

- The user provides the {feature_name} as part of the prompt, or by way of the current branch which will contain the name of the feature, either in whole or prefixed by specs/.
- Verify that the specs/{feature_name} folder exists and has a requirements.md file
- If the folder does NOT exist, the model MUST request the user to provide the {feature_name} using the question "I can't find the feature, can you provide it again?"
- If the requirements.md file does not exist in the folder, the model MUST inform the user that they need to use the requirements skill to create it first.
- If a decision_log.md file exists in the specs/{feature_name} folder, the decisions in there MUST be followed.
- The model MUST create a 'specs/{feature_name}/design.md' file if it doesn't already exist
- The model MUST identify areas where research is needed based on the feature requirements
- The model MUST conduct research and build up context in the conversation thread
- The model SHOULD NOT create separate research files, but instead use the research as context for the design and implementation plan
- The model MUST summarize key findings that will inform the feature design
- The model SHOULD cite sources and include relevant links in the conversation
- The model MUST create a design document at 'specs/{feature_name}/design.md'
- The model MUST incorporate research findings directly into the design process
- The design document SHOULD use the following sections when they apply. Sections that do not apply to the feature MUST be omitted rather than padded with boilerplate:
  - Overview (1-3 sentences on what is being built and why)
  - Architecture (only what changes or is added; do not describe the existing system unless directly relevant — integration points ARE always relevant)
  - Components and Interfaces (sketch types/signatures; add a one-line behavioral note when the contract is not obvious from the name)
  - Data Models (omit if no new or changed models)
  - Error Handling (omit if no new failure modes)
  - Testing Strategy
- When writing the Testing Strategy section, the model SHOULD evaluate acceptance criteria for property-based testing (PBT) candidates:
  - Review requirements that express universal guarantees (invariants, round-trip behavior, idempotence)
  - For components like parsers, serializers, data structures, or algorithms, consider whether PBT would provide better coverage than example-based tests alone
  - If PBT is appropriate, specify: the properties to test, the framework to use (based on project language), and the input generation approach
  - If PBT is not appropriate for the feature, this should be omitted from the Testing Strategy
- The model SHOULD include diagrams or visual representations when appropriate (use Mermaid for diagrams if applicable)
- The model MUST ensure the design addresses all feature requirements identified during the clarification process
- The model MUST use tools like context7 to retrieve relevant information about the libraries and tools

**Contracts and Integration Points — Do Not Cut:**

Even when trimming prose, the following MUST be captured somewhere in the design (usually in Architecture or Components and Interfaces). A signature alone is not a contract.

- **Behavioral contracts** that are not self-evident from the name or signature: idempotence, ordering guarantees, invariants, side effects, concurrency/transaction requirements, performance expectations that constrain the implementation.
- **Integration points**: exactly where new code plugs into existing code — the hook, interface, call site, event, middleware slot, or extension point. Name the file or symbol when it is not otherwise obvious.
- **File/module placement** for new subsystems where no existing convention clearly dictates the location. A one-liner is enough; skip this only when the placement is unambiguous from project conventions.

**Pattern Extension Audit:**
When the design extends an existing pattern to a new type (e.g., adding table row sub-blocks alongside list item sub-blocks, or adding a new export format alongside an existing one), the model MUST:
1. Search the codebase for all references to the existing pattern's key functions and types (e.g., grep for `allListItemIds`, `listItemId`, the sub-ID format string)
2. List every call site and determine whether each needs a parallel implementation for the new type
3. Include this parity audit as a table or checklist in the Architecture section, with an explicit "needs equivalent: yes/no" decision for each site and a brief rationale

This prevents bugs where the primary touch points are covered but secondary consumers (e.g., export formatters, heading path indexes, section note counts) are missed.

**UI Consistency References:**
When the design introduces a UI element that has an existing equivalent in the codebase (e.g., an indicator, button, or affordance), the design MUST reference the existing pattern as the baseline. The design SHOULD NOT describe visual properties from scratch when an equivalent already exists — instead, it should state which existing element to match and only describe deviations.

**Self-Review Checklist (before skill review):**
Before triggering skill reviews, the model MUST verify:
- [ ] Each requirement from requirements.md has a corresponding design element
- [ ] All acceptance criteria can be traced to specific components or interfaces
- [ ] Data models support all required operations from the requirements
- [ ] Error handling covers failure modes implied by requirements
- [ ] Testing strategy includes tests for each acceptance criterion
- [ ] No design elements exist without a corresponding requirement (scope creep check)
- [ ] No design element implements or prepares for a capability listed in the requirements' Non-Goals / Out-of-Scope section
- [ ] If extending an existing pattern, all call sites of the original pattern are audited and the design addresses each one
- [ ] UI elements that have existing equivalents reference the existing pattern rather than defining visual properties from scratch
- [ ] Every paragraph carries a decision, constraint, or non-obvious fact — none exist solely to introduce, summarize, or restate the requirements
- [ ] No sections are padded with boilerplate; inapplicable sections are omitted entirely
- [ ] No hyperbolic or marketing language ("comprehensive", "robust", "seamless", etc.)
- [ ] Non-obvious behavioral contracts (idempotence, ordering, invariants, side effects, transaction/concurrency requirements) are stated, not just implied by signatures
- [ ] Integration points with existing code are named (hook, call site, interface, event, extension point)
- [ ] For new subsystems, file/module placement is stated when not dictated by existing project conventions

**Self-Validation via Explanation:**
- The model MUST use the explain-like skill (invoke the Skill tool with skill="explain-like") to explain the design at multiple expertise levels (beginner, intermediate, expert)
- This serves as a self-review mechanism: if the design cannot be clearly explained at each level, it may indicate gaps, overcomplexity, or logic issues
- The model SHOULD address any issues discovered during this explanation process before proceeding to skill reviews

- The model MUST use relevant skills to receive feedback on the design, after writing the initial design. The requirements MUST always take precedence over this feedback.
- The model MUST highlight design decisions and their rationales in a decision log document at specs/{feature_name}/decision_log.md
- The model MUST ask the user for input on specific technical decisions during the design process
- When asking the user questions and offering options, the model MUST use the AskUserQuestion tool.
- After updating the design document, the model MUST use the Task tool with subagent_type="general-purpose" to run the design-critic skill (invoke the Skill tool with skill="design-critic"), and the Task tool with subagent_type="peer-review-validator" to review the document and provide its questions to the user.
- After the review by the skills, the model MUST ask the user "Does the design look good?"
- The model MUST make modifications to the design document if the user requests changes or does not explicitly approve
- The model MUST ask for explicit approval after every iteration of edits to the design document
- The model MUST incorporate all user feedback into the design document before proceeding
