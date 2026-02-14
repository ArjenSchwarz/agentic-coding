---
name: swiftui-forms
description: Build macOS 26+ SwiftUI forms using Liquid Glass design language. Use when creating preferences panes, inspectors, configuration screens, or settings views in SwiftUI for macOS 26. Provides Grid-based layout with right-aligned labels, correct control sizing, and correct glass modifier usage (glassEffect as background for containers, glassEffect in ZStack for rare tiles). Triggers on "build a form", "settings screen", "preferences view", "inspector panel", or any macOS SwiftUI form layout work.
# model: inherit
# allowedTools: []
---

# Liquid Glass Forms (macOS 26+)

## Two-Layer Architecture

- **Glass layer**: toolbars, sidebars, inspector shells, section containers (structural)
- **Content layer**: form rows and fields (solid/neutral)

Glass is for the navigation/control layer floating above content, not a blanket background for every input.

## Glass Modifier Usage

On macOS 26, there is ONE glass modifier: `glassEffect(_:in:)`.

- **Section containers**: Apply as a `.background {}` on a `RoundedRectangle`
- **Special tiles/callouts**: Apply in a `ZStack` on a shape (rare)

⚠️ `glassBackgroundEffect(displayMode:)` is **visionOS-only** — it does NOT compile on macOS.

## Default Layout Pattern

Use `Grid` + `FormRow` with a `labelWidth` sized to the longest label. Only fall back to `Form` for trivial System Settings-style preference lists.

```swift
struct MacConfigView: View {
    // Size to longest label. ~90 for short labels like "Name", "Email".
    // Scale up only for genuinely long labels like "Notification Frequency".
    private let labelWidth: CGFloat = 90

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 28) {
                LiquidGlassSection(title: "General") {
                    Grid(alignment: .leadingFirstTextBaseline,
                         horizontalSpacing: 16, verticalSpacing: 14) {
                        FormRow("Name", labelWidth: labelWidth) {
                            TextField("", text: $name)
                        }
                        FormRow("Role", labelWidth: labelWidth) {
                            Picker("", selection: $role) {
                                ForEach(Role.allCases, id: \.self) { r in
                                    Text(r.displayName).tag(r)
                                }
                            }
                            .labelsHidden()
                            .pickerStyle(.menu)
                            .fixedSize()
                        }
                        FormRow("Sync", labelWidth: labelWidth) {
                            Toggle("", isOn: $syncEnabled).labelsHidden()
                        }
                    }
                }

                HStack {
                    Spacer()
                    Button("Save") { save() }
                        .buttonStyle(.borderedProminent)
                        .disabled(!isValid)
                }
            }
            .padding(32)
            .frame(maxWidth: 760, alignment: .leading)
        }
    }
}
```

## Building Blocks

### FormRow

Right-aligned label column + control column inside a `GridRow`. The content column uses `.frame(maxWidth: .infinity, alignment: .leading)` to ensure all controls — including intrinsically-sized ones like Picker and Toggle — left-align consistently.

Without this, intrinsically-sized controls centre in the grid column while TextFields stretch to fill, creating a misaligned layout.

```swift
struct FormRow<Content: View>: View {
    let label: String
    let labelWidth: CGFloat
    let content: Content

    init(_ label: String, labelWidth: CGFloat,
         @ViewBuilder content: () -> Content) {
        self.label = label
        self.labelWidth = labelWidth
        self.content = content()
    }

    var body: some View {
        GridRow {
            Text(label)
                .foregroundStyle(.secondary)
                .frame(width: labelWidth, alignment: .trailing)
            content
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}
```

### LiquidGlassSection

Use `glassEffect(.regular, in:)` as a `.background {}` for section containers:

```swift
struct LiquidGlassSection<Content: View>: View {
    let title: String
    let content: Content

    init(title: String, @ViewBuilder content: () -> Content) {
        self.title = title
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title).font(.headline)
            content
                .padding(18)
                .background {
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .fill(.clear)
                        .glassEffect(.regular, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
                }
        }
    }
}
```

### GlassTile (rare, special callouts only)

Use `glassEffect(_:in:)` in a ZStack only for summary tiles, callouts, or inspector headers. Never for field rows or dense forms.

```swift
struct GlassTile<Content: View>: View {
    let content: Content
    init(@ViewBuilder content: () -> Content) { self.content = content() }

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(.clear)
                .glassEffect(.regular, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
            content.padding(16)
        }
    }
}
```

## Control Sizing Rules

The outer container (`.frame(maxWidth: 760)`) constrains overall form width. Within that, let controls take the space they need:

| Control type | Sizing |
|---|---|
| Text fields | No maxWidth — fill the row via FormRow |
| Pickers | `.fixedSize()` — sizes to content, left-aligned by FormRow |
| Numeric fields | Fixed `width: 70-120` |
| Toggles | `.labelsHidden()` in right column |

Do NOT add `maxWidth` to text fields or pickers — it creates cramped fields with wasted space alongside them. The container handles overall width.

Pickers: `.pickerStyle(.menu)` by default.

## Label Width Sizing

Size `labelWidth` to the longest label in the form, not a fixed large number.

- **Short labels** ("Name", "Type", "Status"): ~90
- **Medium labels** ("Description", "Environment"): ~100-120
- **Long labels** ("Notification Frequency"): ~160+

A too-wide label column wastes horizontal space and pushes fields into the right half of the form where they get cramped.

## Multi-Platform Views (iOS + macOS in same file)

When a view provides both iOS and macOS layouts, wrap platform-specific computed properties in `#if os()` — not just the branch in `body`.

```swift
var body: some View {
    NavigationStack {
        #if os(macOS)
        macOSForm
        #else
        iOSForm
        #endif
    }
}

#if os(iOS)
private var iOSForm: some View {
    Form { /* ... */ }
        .navigationBarTitleDisplayMode(.inline)  // iOS-only API
}
#endif

#if os(macOS)
private var macOSForm: some View {
    ScrollView { /* Grid layout */ }
}
#endif
```

Why: The compiler type-checks all computed properties regardless of which branch `body` takes. iOS-only modifiers like `navigationBarTitleDisplayMode` fail on macOS even if the property is only called from an `#if os(iOS)` branch.

Shared components (e.g. MetadataSection) should emit platform-adaptive content:
- **iOS**: wrap in `Section("Title")` for Form/List compatibility
- **macOS**: emit bare content (caller wraps in `LiquidGlassSection`)

## Validation

Inline, indented under the field column. Disable primary action until valid.

```swift
Text("Invalid email address")
    .font(.caption)
    .foregroundStyle(.red)
    .padding(.leading, labelWidth + 16)
```

## Checklist

1. `Grid` + `FormRow` with `labelWidth` sized to the longest label
2. Text fields fill the row — no maxWidth. Pickers use `.fixedSize()`
3. `.glassEffect(.regular, in:)` as `.background {}` for section containers only
4. `glassEffect(_:in:)` in a ZStack only for special tiles/callouts
5. Readability works with reduced transparency (no glass-only separation)
6. Content layer stays visually calm
7. Wrap platform-specific computed properties in `#if os()` blocks
