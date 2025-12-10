---
paths: **/*.swift
---

# Swift Language Rules

## SwiftData and CloudKit Testing

### Problem: Shared ModelContainer Initialization in Tests

When using SwiftData with CloudKit and App Groups, the shared `ModelContainer` requires entitlements (App Groups, CloudKit) that are not available in the test environment. If you use `static let` for the shared container, it will be initialized when the test runner launches the app as a test host, causing a crash before any test code runs.

**Anti-pattern:**
```swift
enum ModelContainerConfig {
    // This will crash in tests - App Group not available
    static let shared: ModelContainer = {
        guard let groupURL = FileManager.default.containerURL(
            forSecurityApplicationGroupIdentifier: appGroupID
        ) else {
            fatalError("App Group container is not available.")
        }
        // ... create container
    }()
}
```

**Solution: Test Environment Detection**

Use lazy initialization with automatic test environment detection:

```swift
enum ModelContainerConfig {
    nonisolated(unsafe) private static var _shared: ModelContainer?

    private static var isRunningTests: Bool {
        NSClassFromString("XCTestCase") != nil ||
        ProcessInfo.processInfo.environment["XCTestConfigurationFilePath"] != nil
    }

    static var shared: ModelContainer {
        if let container = _shared {
            return container
        }
        if isRunningTests {
            _shared = inMemory()
        } else {
            _shared = createProductionContainer()
        }
        return _shared!
    }

    static func inMemory() -> ModelContainer {
        let config = ModelConfiguration(
            schema: schema,
            isStoredInMemoryOnly: true,
            cloudKitDatabase: .none
        )
        return try! ModelContainer(for: schema, configurations: [config])
    }
}
```

**Key Points:**
- `NSClassFromString("XCTestCase")` returns non-nil when running in a test environment
- `XCTestConfigurationFilePath` environment variable is set by Xcode during test runs
- Use `nonisolated(unsafe)` for the backing storage since it's only written once at startup
- Tests automatically get an in-memory container; production gets the CloudKit-enabled container

### App Group Provisioning Issues

When using App Groups, `FileManager.containerURL(forSecurityApplicationGroupIdentifier:)` may return a URL even when:
- The App Group isn't provisioned in the Apple Developer portal
- Running with "Sign to Run Locally" instead of a proper provisioning profile

The sandbox will block file creation, causing `ModelContainer` initialization to fail. Handle this with a fallback:

```swift
private static func createProductionContainer() -> ModelContainer {
    // Try App Group location first
    if let groupURL = FileManager.default.containerURL(
        forSecurityApplicationGroupIdentifier: appGroupID
    ) {
        let storeURL = groupURL.appendingPathComponent("app.store")
        let config = ModelConfiguration(schema: schema, url: storeURL, cloudKitDatabase: .private(cloudKitID))

        do {
            return try ModelContainer(for: schema, configurations: [config])
        } catch {
            // Sandbox blocked - fall through to default location
            print("⚠️ Warning: App Group container failed, using default location.")
        }
    }

    // Fallback: Use default location (works but won't support App Extensions)
    let config = ModelConfiguration(schema: schema, cloudKitDatabase: .private(cloudKitID))
    return try! ModelContainer(for: schema, configurations: [config])
}
```

### Design Consideration

When designing SwiftData persistence with CloudKit/App Groups, always plan for testability from the start. Include test environment detection in your initial design rather than treating it as an afterthought.

## Swift 6 Concurrency

### MainActor by Default

In Xcode 26+ projects, new code defaults to `@MainActor` isolation. Use `@concurrent` to explicitly opt out when needed for background work.

### SwiftData and Actors

- `ModelContext` is not `Sendable` - keep context access on the same actor
- Use `@MainActor` for view models that access SwiftData
- For background processing, create a new `ModelContext` on that actor

## SwiftUI Best Practices

### iOS 26 / macOS Tahoe Liquid Glass

Liquid Glass is a translucent material that reflects and refracts surrounding content. Key principle: **glass cannot sample other glass** - having nearby glass elements in different containers causes visual artifacts like unwanted reflections.

**General Rules:**
- Do NOT add `toolbarBackground()` or `toolbarColorScheme()` modifiers to NavigationSplitView
- Let the system apply Liquid Glass styling automatically
- Liquid Glass is for the **navigation layer only** - never apply to content itself

**macOS-Specific Issues:**

On macOS, pushed views in a NavigationStack (inside NavigationSplitView's detail column) can show reflection artifacts under the navigation bar. The fix is to hide the scroll content background:

```swift
struct DetailView: View {
    var body: some View {
        ScrollView {
            // content
        }
        .navigationTitle("Title")
        #if os(macOS)
        .scrollContentBackground(.hidden)
        #endif
    }
}
```

**Where to Apply `.backgroundExtensionEffect()`:**
- Apply to the **sidebar List**, not the detail view
- This modifier extends content beyond the safe area with a mirrored/blurred effect

```swift
NavigationSplitView {
    List { /* ... */ }
        .backgroundExtensionEffect()  // On sidebar
} detail: {
    DetailView()  // No backgroundExtensionEffect here
}
```

### NavigationSplitView

```swift
NavigationSplitView {
    SidebarView()
} detail: {
    DetailView()
}
// No toolbar styling modifiers - let Liquid Glass apply
```

### Toolbar Placement in NavigationSplitView

Toolbars attached directly to `NavigationSplitView` don't display properly on iOS. Place toolbars on the sidebar view instead:

**Anti-pattern (toolbar not visible on iOS):**
```swift
NavigationSplitView {
    SidebarView()
} detail: {
    DetailView()
}
.toolbar {
    ToolbarItem(placement: .primaryAction) {
        Button("Add", systemImage: "plus") { }
    }
}
```

**Correct (toolbar visible in navigation bar):**
```swift
struct SidebarView: View {
    var body: some View {
        List { /* ... */ }
            .navigationTitle("App Name")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button("Add", systemImage: "plus") { }
                }
            }
    }
}
```

On iOS with compact width, NavigationSplitView collapses to a navigation stack. The toolbar must be on the view that owns the navigation bar (the sidebar) for buttons to appear correctly.

### NavigationSplitView: Platform-Specific Navigation Patterns

NavigationSplitView behaves differently on iOS vs macOS, requiring platform-specific code for navigation:

**The Problem:**
- On macOS, `navigationDestination(for:)` works reliably in the detail column
- On iOS, the sidebar collapses into a navigation stack, and `.navigationDestination(for:)` inside the detail column may not function correctly for child navigation

**Solution: Use `#if os()` for Platform-Specific Navigation**

```swift
// In the list view (inside detail column)
ForEach(items) { item in
    #if os(macOS)
    // macOS: Use value-based NavigationLink with navigationDestination
    NavigationLink(value: item) {
        ItemRow(item: item)
    }
    #else
    // iOS: Use destination-based NavigationLink (works better in collapsed sidebar)
    NavigationLink {
        ItemDetailView(item: item)
    } label: {
        ItemRow(item: item)
    }
    #endif
}

#if os(macOS)
.navigationDestination(for: Item.self) { item in
    ItemDetailView(item: item)
}
#endif
```

**Key Points:**
- On macOS, the three-column NavigationSplitView maintains separate navigation stacks, so `navigationDestination(for:)` works correctly
- On iOS in compact width, everything collapses to a single navigation stack - destination-based NavigationLink is more reliable
- Use `#if os(macOS)` / `#else` to provide platform-specific implementations
- For sidebar-level navigation on iOS, use NavigationLink with inline destinations rather than selection bindings

**When Sidebar Contains the Primary Navigation:**

On iOS, if navigation originates from the sidebar (e.g., tapping a category), use destination-based NavigationLinks in the sidebar itself:

```swift
struct SidebarView: View {
    var body: some View {
        List {
            #if os(macOS)
            ForEach(categories) { category in
                Text(category.name)
                    .tag(category)
            }
            #else
            ForEach(categories) { category in
                NavigationLink {
                    CategoryDetailView(category: category)
                } label: {
                    Text(category.name)
                }
            }
            #endif
        }
        #if os(macOS)
        .onChange(of: selectedCategory) { _, newValue in
            // Handle category change on macOS
        }
        #endif
    }
}
```

### CommandGroup Menu Placement

When adding items to the macOS menu bar with `CommandGroup`, use `.before` instead of `.after` with `.newItem` to ensure your custom "New" commands appear above the system ones:

**Anti-pattern (command appears after system items):**
```swift
CommandGroup(after: .newItem) {
    Button("New Snippet") { }
        .keyboardShortcut("n", modifiers: .command)
}
```

**Correct (command appears at logical position):**
```swift
CommandGroup(before: .newItem) {
    Button("New Snippet") { }
        .keyboardShortcut("n", modifiers: .command)
    Divider()
}
```

## Testing

### Swift Testing Framework

- Use `@Suite("Name")` to group related tests
- Use `@Test("Description")` for individual test cases
- Use `#expect()` instead of XCTAssert functions
- Use `@MainActor` on tests that access SwiftData

### In-Memory ModelContainer for Tests

Always provide an `inMemory()` factory for unit tests:

```swift
static func inMemory() -> ModelContainer {
    let config = ModelConfiguration(
        schema: schema,
        isStoredInMemoryOnly: true,
        cloudKitDatabase: .none  // Disable CloudKit for tests
    )
    return try! ModelContainer(for: schema, configurations: [config])
}
```

### Test Organization

- Place `*_test.swift` files alongside source code or in a dedicated test target
- Use map-based test tables for parameterized tests
- Mark test helpers with appropriate access control

## CloudKit Constraints

When using SwiftData with CloudKit:

- All properties must have default values or be optional
- Cannot use `@Attribute(.unique)` constraints
- Arrays (like `[String]` for tags) are stored as binary data and cannot be queried with predicates - filter in memory after fetching
- Use private database for user data

## Error Handling Patterns

### Fatal Errors for Configuration

For personal/single-developer apps, use `fatalError()` for configuration errors that should be caught during development:

```swift
guard let groupURL = FileManager.default.containerURL(
    forSecurityApplicationGroupIdentifier: appGroupID
) else {
    fatalError("App Group container is not available. Check entitlements.")
}
```

This surfaces configuration problems immediately rather than hiding them behind fallback behavior.

### Failable Initializers for Validation

Use failable initializers when creation may fail due to invalid input:

```swift
init?(text: String, tags: [String] = []) {
    guard Self.isValid(text: text) else { return nil }
    // ... initialization
}
```

## Property Access Patterns

### Mutation Methods for Timestamp Tracking

When properties need side effects (like updating `modifiedAt`), use mutation methods instead of direct property access:

```swift
@Model
final class Snippet {
    private(set) var text: String = ""
    private(set) var tags: [String] = []
    var modifiedAt: Date = Date.now

    @discardableResult
    func setText(_ newText: String) -> Bool {
        guard Self.isValid(text: newText) else { return false }
        self.text = newText
        self.modifiedAt = Date.now
        return true
    }
}
```

Use `private(set)` to enforce access through mutation methods.

## App Intents

### Parameter Types for Shortcuts Compatibility

When designing App Intents for use with Shortcuts, prefer simple types over arrays for user-facing parameters. Shortcuts handles arrays awkwardly, requiring users to build lists manually.

**Anti-pattern (arrays are cumbersome in Shortcuts):**
```swift
@Parameter(title: "Tags", default: [])
var tags: [String]
```

**Better (comma-separated string is easier for users):**
```swift
@Parameter(title: "Tags", description: "Comma-separated list of tags", default: "")
var tagsInput: String

func perform() async throws -> some IntentResult {
    let tags = tagsInput
        .split(separator: ",")
        .map { $0.trimmingCharacters(in: .whitespaces).lowercased() }
        .filter { !$0.isEmpty }
    // Use parsed tags...
}
```

### Predicate Combination in iOS 26+

iOS 26 adds `evaluate()` for combining predicates dynamically. This is useful when building queries with optional filters:

```swift
let searchPredicate: Predicate<Snippet>?
let datePredicate: Predicate<Snippet>?

// Build predicates based on parameters...

switch (searchPredicate, datePredicate) {
case let (search?, date?):
    descriptor.predicate = #Predicate<Snippet> {
        search.evaluate($0) && date.evaluate($0)
    }
case let (search?, nil):
    descriptor.predicate = search
case let (nil, date?):
    descriptor.predicate = date
case (nil, nil):
    break
}
```

**Note:** This only works for properties that CloudKit can query (scalar types). Arrays stored as binary data still require in-memory filtering.

## NavigationSplitView on iPad/iOS

### Selection-Based Navigation for iPad Default Selection

On iPad, to show a default detail view when the app launches (avoiding a blank detail column), use selection-based navigation instead of destination-based NavigationLinks in the sidebar:

**Problem:** With destination-based NavigationLinks, the detail column is empty on launch.

**Solution:** Use `List(selection:)` with tags and render the detail view based on selection state:

```swift
struct ContentView: View {
    @State private var selection: String? = "__all__"  // Default selection

    var body: some View {
        NavigationSplitView {
            List(selection: $selection) {
                Text("All Items")
                    .tag("__all__")
                ForEach(categories, id: \.self) { category in
                    Text(category)
                        .tag(category)
                }
            }
        } detail: {
            if let selection {
                let filter = (selection == "__all__") ? nil : selection
                DetailView(filter: filter)
            }
        }
    }
}
```

### Clearing Navigation Path When Sidebar Selection Changes

When using `NavigationStack` inside the detail column, changing sidebar selection won't automatically pop pushed views. Maintain a `NavigationPath` and clear it when selection changes:

```swift
struct DetailContentView: View {
    let filterTag: String?
    @State private var navigationPath = NavigationPath()

    var body: some View {
        NavigationStack(path: $navigationPath) {
            ListView()
                .navigationDestination(for: Item.self) { item in
                    ItemDetailView(item: item)
                }
        }
        .onChange(of: filterTag) { _, _ in
            navigationPath = NavigationPath()  // Pop back to list
        }
    }
}
```

### Avoid List Selection Conflict with NavigationLink

Don't use `List(selection:)` and `NavigationLink(value:)` together on iOS - the selection gesture consumes taps, preventing NavigationLink from working:

**Anti-pattern:**
```swift
List(selection: $selected) {
    ForEach(items) { item in
        NavigationLink(value: item) { Text(item.name) }
    }
}
```

**Correct - use one or the other:**
```swift
// Option 1: Selection-based (for sidebar)
List(selection: $selected) {
    ForEach(items) { item in
        Text(item.name).tag(item)
    }
}

// Option 2: NavigationLink-based (for detail list)
List {
    ForEach(items) { item in
        NavigationLink(value: item) { Text(item.name) }
    }
}
```

### Searchable Modifier Placement

Always place `.searchable()` at a level that remains visible regardless of content. If placed only on the content view that gets replaced when results are empty, the search bar disappears:

**Anti-pattern:**
```swift
Group {
    if results.isEmpty {
        ContentUnavailableView.search(text: searchText)
    } else {
        ResultsList()
            .searchable(text: $searchText)  // Disappears when empty!
    }
}
```

**Correct:**
```swift
Group {
    if results.isEmpty {
        ContentUnavailableView.search(text: searchText)
    } else {
        ResultsList()
    }
}
.searchable(text: $searchText)  // Always visible
```

## Form Row Sizing on iOS

iOS Forms apply minimum row heights. Use `.listRowInsets()` to reduce padding for custom content that should be more compact:

```swift
Form {
    Section("Tags") {
        TagInputField(tags: $tags)
            .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))
    }
}
```

## Shared ViewModel Mutation Pitfalls

When using `@Observable` class ViewModels that are passed through navigation, avoid mutating the shared instance for view-specific filtering. Instead, filter locally in the view:

**Anti-pattern (mutates shared state):**
```swift
struct DetailView: View {
    let viewModel: ViewModel  // Reference type

    var body: some View { ... }

    .task {
        viewModel.filterTag = tag  // Affects sidebar counts!
        await viewModel.fetch()
    }
}
```

**Correct (filter locally):**
```swift
struct DetailView: View {
    let viewModel: ViewModel
    let filterTag: String?

    private var displayedItems: [Item] {
        guard let tag = filterTag else { return viewModel.allItems }
        return viewModel.allItems.filter { $0.tags.contains(tag) }
    }

    var body: some View {
        List(displayedItems) { ... }
    }
}
