# Offline CS2103T convention rules

Adapted from the bundled CS2103T standards skill, whose references were assembled on 2026-08-17. Source links and precedence are in `instructions.md`. Java basic/intermediate and Git subject rules are mandatory; Markdown and documentation guidance remain optional unless adopted by the repository.

# Course requirements and precedence

## Requirement levels

| Area | Level | Course rule |
|---|---|---|
| Java | Required | Follow all basic and intermediate rules in the bundled Java convention. |
| Java | Optional | Follow the advanced Java rules listed separately in the bundled Java convention. |
| Git | Required | Follow the bundled Git commit-message subject rules. |
| Git | Conditional | A commit body is optional; if present, follow at least the bundled basic body rules. |
| Markdown | Optional | Follow the bundled Markdown convention. |
| Documentation | Optional | Follow the bundled developer-documentation style. |

Do not use the less demanding CS2113/TIC2002 Java requirement for CS2103T. CS2103T requires both basic and intermediate Java rules.

## Uncovered aspects

When the Java or Git rules do not cover an aspect:

- Choose a reasonable style.
- Stay consistent with existing code.
- In a team project, ensure the whole team follows the same convention.

## Rule precedence

Apply guidance in this order:

1. Explicit assignment or course requirement
2. CS2103T requirement levels in this file
3. Repository-local instructions and agreed team conventions
4. The bundled topic-specific convention
5. General language conventions

Do not turn optional guidance into a required violation unless the repository explicitly adopts it.

## Offline status

This package contains the operational content needed to apply the course rules without following external links. The rule set was assembled from the CS2103T standards page, SE-EDU Java/Git/Markdown conventions, and Google developer-documentation guidance as available on 2026-08-17.


# Java conventions

## Contents

- Naming
- Layout
- Statements and declarations
- Comments and Javadoc
- Optional advanced rules

All rules before the optional advanced section are required for CS2103T.

## Naming

- Write package names in lowercase. For school projects, start with the group or project name and then logical subpackages. Do not claim an NUS-owned namespace such as `edu.nus.comp`.
- Name classes and enums with PascalCase nouns, e.g. `Line` and `AudioSystem`.
- Name variables with camelCase.
- Name constants with SCREAMING_SNAKE_CASE. Treat a field as a constant only when it is `static final` and deeply immutable or never observably changes.
- Name methods with camelCase verbs, e.g. `getName` and `computeTotalWidth`.
- Permit test names in the form `featureUnderTest_testScenario_expectedBehavior`; omit later parts when the test genuinely covers the broader scope.
- Keep acronyms in normal word case inside identifiers: use `exportHtmlSource`, not `exportHTMLSource`.
- Write names in English.
- Use longer names for larger scopes; short scratch names such as `i`, `j`, and `k` are acceptable in small scopes. Reserve later letters for nested loops.
- Make boolean names read as booleans, normally using prefixes such as `is`, `has`, `was`, `can`, or `should`.
- Name a boolean setter parameter consistently, e.g. `setFound(boolean isFound)`.
- Use plural names for collections and arrays.
- Give associated constants a common prefix so they group naturally, e.g. `COLOR_RED`, `COLOR_GREEN`, and `COLOR_BLUE`.

## Layout

- Indent with four spaces. Do not use tabs.
- Keep lines below 110 characters when practical; 120 characters is the hard limit.
- Indent continuation lines eight spaces beyond the parent line.
- Wrap for readability: break after commas and before operators, dots, type-bound ampersands, and multi-catch pipes.
- Keep a method or constructor name attached to its opening parenthesis.
- Prefer a higher-level expression break over a deeply nested break.
- Use K&R braces: place the opening brace at the end of the control or declaration line and the closing brace on its own line.
- Always use braces for loops and conditionals, including single-statement bodies.
- Format `if`/`else`, `for`, `while`, `do`/`while`, `switch`, `try`/`catch`/`finally`, and method declarations consistently with K&R layout.
- Indent `case` labels one level inside `switch` and their statements one further level.
- Add `// Fallthrough` when a classic switch intentionally continues into the next case. Arrow-style switch cases do not need it.
- Put spaces around binary and ternary operators, after commas and semicolons, and between control-flow keywords and `(`.
- Do not add spaces immediately inside parentheses.
- Separate logical units in a block with one blank line. Do not add blank lines merely to spread closely related statements apart.

## Statements and declarations

- Put every class in a package.
- Keep import ordering consistent throughout the project. Separate logical import groups with blank lines if the project does so.
- Import classes explicitly; do not use wildcard imports.
- Attach array brackets to the type: use `int[] values`, not `int values[]`.
- Initialize variables where declared when a valid value is available.
- Declare variables in the smallest practical scope.
- Prefer leaving a variable temporarily uninitialized over assigning a misleading placeholder.
- Do not expose public mutable class variables unless the class is a behavior-free data class. Public constants are exempt.
- Put each conditional body on separate lines; do not write a one-line `if` body.
- Put each loop body in braces, even when it contains one statement.

## Comments and Javadoc

- Write comments in English, avoid local slang, and use one spelling variant consistently.
- Write descriptive header comments for classes and public methods.
- Header comments may be omitted for self-explanatory getters/setters, overrides whose inherited documentation applies exactly, and test-only classes or methods.
- Describe what a public API promises, not merely how its implementation works.
- Format Javadoc with `/**` on its own line, aligned leading `*`, a space after each `*`, and no blank line between the block and declaration.
- Start Javadoc with a short summary sentence. For methods, prefer a third-person verb such as “Returns”, “Adds”, or “Sends”.
- Separate the main description from tags with a blank Javadoc line.
- End parameter and return descriptions with punctuation.
- Either document all parameters or omit all `@param` tags when every name is self-explanatory and the main text already explains them.
- Omit `@return` for `void` or when the return is already unambiguous from the description.
- Use `{@inheritDoc}` when inherited documentation needs a local extension.
- Permit a one-line Javadoc comment for a simple member, e.g. `/** Number of active connections. */`.
- Indent comments with the code they describe. Trailing comments are allowed when they stay readable.

## Optional advanced rules

These rules are recommended but not mandatory for CS2103T unless the repository adopts them:

- Put closely related classes in one cohesive package.
- Organize class/interface members consistently: class documentation, declaration, constants, static fields, instance fields, constructors, public methods, protected methods, private methods, then nested types, unless project style specifies another clear order.
- Order method modifiers consistently using the conventional Java sequence, such as access modifier before `abstract`, `static`, `final`, `synchronized`, `native`, and `strictfp`.
- Avoid unnecessary `this.` qualifiers when no disambiguation is needed.
- Add header comments to non-trivial private methods.


# Git conventions

## Commit subject: required

- Give every commit a meaningful subject.
- Aim for 50 characters or fewer; 72 characters is the hard limit.
- Use imperative mood, as if completing “This commit will …”: use `Add README`, not `Added README` or `Adding README`.
- Capitalize the first letter of the subject, except when an intentionally lowercase category precedes a colon.
- Do not end the subject with a period.
- Optionally prefix a useful scope or category followed by a colon, e.g. `Parser: Handle empty input` or `chore: Update release date`.

## Commit body: conditional

A body is optional for the course. If one is present, apply these rules:

- Separate the subject and body with one blank line.
- Wrap body lines at 72 characters.
- Separate paragraphs with blank lines.
- Use bullet lists when they improve clarity.
- Explain what changed and why; let the diff show how.
- Give enough context for a reviewer to judge the change without first reading the diff.
- For a non-trivial change, cover the current situation, why it should change, what is being done, why that approach was chosen, and other relevant information.
- Use present tense for the current situation and imperative mood for the action being taken.
- Avoid filler such as “currently” or “originally” when the timeline is already clear.
- Avoid repeating details already stated in code comments.
- Split the commit if its description becomes long because it combines unrelated changes.

## Branch names: reference convention

- Use a meaningful kebab-case name containing relevant keywords, e.g. `refactor-ui-tests`.
- For an issue-related branch, prefer `issueNumber-keywords`, e.g. `1234-ui-freeze-error`.

The CS2103T page explicitly requires the subject rules. Treat the body rules as conditional when a body exists, and treat branch naming as a consistency convention unless an assignment makes it mandatory.


# Markdown conventions

These rules are optional course recommendations unless the repository adopts them.

- Use GitHub Flavored Markdown syntax strictly; do not rely on a renderer forgiving malformed syntax.
- Do not hard-wrap natural-language paragraphs at a fixed column width.
- Put a blank line before every list.
- Put a blank line before every code block.
- Put one space after heading markers: use `# Heading`, not `#Heading`.
- Put a blank line after a heading and before its content.
- Prefix every line of a multiline blockquote with `>`.
- Use `1.` for every item in an ordered list so insertions do not require renumbering.
- Use `*` for unordered-list bullets.
- Use `_text_` for italics.
- Use fenced code blocks with an accurate language identifier for multiline code.
- Keep heading hierarchy, indentation, and list nesting consistent within the document.

Do not report these optional preferences as mandatory CS2103T violations unless repository-local guidance requires them.


# Developer-documentation style

These rules are optional course recommendations unless the repository adopts them.

## Audience and structure

- Write for the intended reader and the task they need to complete.
- Put the most important information first.
- Use descriptive headings and a logical hierarchy.
- Keep each paragraph focused on one idea.
- Introduce prerequisites before instructions that depend on them.
- Use numbered steps for ordered procedures and bullets for unordered information.
- State the goal or result of a procedure before the steps when it helps orientation.

## Language

- Prefer active voice when the actor matters and the active sentence is clearer.
- Address the reader as “you”; avoid “we” when it ambiguously means the writer, product, or reader.
- Use present tense for current product behavior and imperative verbs for instructions.
- Use clear, familiar words and concise sentences.
- Define unfamiliar terms and abbreviations at first use.
- Use terminology consistently; do not switch names for the same concept.
- Avoid needless jargon, idioms, slang, and culture-specific expressions.
- Avoid language that assigns blame to the reader.
- Use inclusive, respectful language.

## Procedures and cautions

- Begin each step with an action when possible.
- Put conditions before the action when the reader must know them first.
- Include only information needed to complete or understand the task.
- State expected results after important steps.
- Put warnings before the action that can cause harm, loss, or an irreversible result.
- Distinguish optional steps from required steps.
- Use parallel grammar across neighboring steps and list items.

## Code, UI, and technical terms

- Use code formatting for commands, filenames, paths, identifiers, literal values, and text the reader must type.
- Use consistent capitalization for UI labels and reproduce visible labels accurately.
- Describe interaction by the visible label and control, e.g. “Select **Save**,” without unnecessary positional directions.
- Use placeholders that are meaningful and visually distinct from literal text.
- Explain command purpose, required location, and important side effects.
- Keep examples realistic, minimal, and internally consistent.

## Links and references

- Use descriptive link text that makes sense out of context; avoid “click here”.
- Link to the most specific relevant destination.
- Avoid repeating the raw destination when descriptive text is clearer.
- Do not rely on a link as a substitute for essential instructions; include the information needed to complete the immediate task.

## Style precedence

Follow project-specific documentation style first, then this bundled guidance. Prefer clarity and consistency for the actual audience when a mechanical style preference would make the document worse.
