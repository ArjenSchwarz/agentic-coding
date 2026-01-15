---
paths: **/*.swift
---

# Swift 6 & SwiftUI Development Rules

Rules for AI agents generating Swift 6 and SwiftUI code targeting iOS 17+/macOS 14+.

---

## Swift 6 Concurrency

### ALWAYS
- Enable Swift 6 language mode with strict concurrency checking
- Mark all ViewModels and observable classes with `@MainActor`
- Use `async/await` for asynchronous operations
- Use `Task {}` only when bridging from synchronous to async context
- Prefer structured concurrency (`async let`, `TaskGroup`) over unstructured `Task` creation
- Check `Task.isCancelled` or call `try Task.checkCancellation()` in long-running operations
- Use `actors` for shared mutable state accessed from multiple concurrent contexts
- Use `Mutex` from the Synchronization library when you need manual thread-safety

### NEVER
- Use `@unchecked Sendable` unless absolutely necessary and document why
- Mutate actor properties directly from outside—use actor methods instead
- Use `DispatchQueue.main.async` for UI updates—use `@MainActor` instead
- Use completion handlers when async/await is available
- Create detached tasks (`Task.detached`) without explicit justification

### PATTERNS
```swift
// ViewModel pattern
@Observable
@MainActor
final class FeatureViewModel {
    var state: ViewState = .idle
    
    func load() async {
        state = .loading
        defer { if Task.isCancelled { state = .idle } }
        do {
            let data = try await service.fetch()
            state = .loaded(data)
        } catch {
            state = .error(error)
        }
    }
}

// Actor for shared state
actor DataCache {
    private var cache: [String: Data] = [:]
    
    func get(_ key: String) -> Data? { cache[key] }
    func set(_ key: String, data: Data) { cache[key] = data }
}
```

---

## Observation Framework (@Observable)

### ALWAYS
- Use `@Observable` macro instead of `ObservableObject` for iOS 17+
- Use `@State` to own @Observable instances in views
- Use `@Bindable` to create bindings from @Observable properties
- Use `@Environment` to inject @Observable dependencies
- Mark `@State` properties as `private`

### NEVER
- Use `ObservableObject`, `@Published`, `@ObservedObject`, or `@StateObject` in new code
- Use `@EnvironmentObject`—use `@Environment` with @Observable instead
- Use `objectWillChange.send()`—@Observable handles this automatically

### PATTERNS
```swift
// Owning an observable
struct ProfileView: View {
    @State private var viewModel = ProfileViewModel()
    
    var body: some View {
        ProfileContent(viewModel: viewModel)
            .task { await viewModel.load() }
    }
}

// Passing for binding
struct ProfileEditor: View {
    @Bindable var viewModel: ProfileViewModel
    
    var body: some View {
        TextField("Name", text: $viewModel.name)
    }
}

// Environment injection (at App level)
@main
struct MyApp: App {
    @State private var appState = AppState()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(appState)
        }
    }
}

// Environment consumption
struct ChildView: View {
    @Environment(AppState.self) private var appState
    // ...
}
```

---

## State Management

### ALWAYS
- Use `@State` for view-local state (toggles, text fields, counts)
- Use `@Binding` when child views need to modify parent state
- Pass bindings with `$` prefix
- Initialize state with sensible defaults

### NEVER
- Use `@State` for reference types—use `@State` with `@Observable` classes
- Declare `@State` without `private` access level
- Share `@State` between unrelated views—lift to common ancestor or use environment

### CHOOSING STATE WRAPPER
| Scenario | Wrapper |
|----------|---------|
| Simple value owned by this view | `@State private var` |
| @Observable owned by this view | `@State private var` |
| Child needs to modify parent's value | `@Binding var` |
| Need binding to @Observable property | `@Bindable var` |
| App-wide or subtree-wide dependency | `@Environment(Type.self)` |
| Reading system values (colorScheme, etc.) | `@Environment(\.keyPath)` |

---

## Navigation

### ALWAYS
- Use `NavigationStack` (not `NavigationView`)
- Use `NavigationPath` for programmatic navigation
- Define routes as `Hashable` enums
- Place `navigationDestination(for:)` directly inside `NavigationStack`, at container level
- Give each tab its own independent `NavigationStack`

### NEVER
- Use `NavigationView`—it's deprecated
- Place `navigationDestination` inside `List`, `LazyVStack`, or `ForEach`
- Store `NavigationPath` at the `App` level—keep it per-scene/per-tab
- Use `NavigationLink(destination:)` for programmatic navigation—use path-based approach

### PATTERNS
```swift
// Route definition
enum Route: Hashable {
    case detail(Item)
    case settings
    case profile(userId: String)
}

// Navigation setup
struct ContentView: View {
    @State private var path = NavigationPath()
    
    var body: some View {
        NavigationStack(path: $path) {
            HomeView(path: $path)
                .navigationDestination(for: Route.self) { route in
                    switch route {
                    case .detail(let item): DetailView(item: item)
                    case .settings: SettingsView()
                    case .profile(let id): ProfileView(userId: id)
                    }
                }
        }
    }
}

// Programmatic navigation
Button("Show Detail") {
    path.append(Route.detail(item))
}

// Deep linking
.onOpenURL { url in
    if let route = Route(from: url) {
        path.append(route)
    }
}
```

---

## View Performance

### ALWAYS
- Pass only required data to child views (not entire model objects)
- Use `Identifiable` conformance or stable `id()` values
- Use lazy containers (`LazyVStack`, `LazyHStack`, `LazyVGrid`) for large collections
- Use `List` for very large datasets (500+ items) that need recycling
- Filter data before `ForEach`, not inside it
- Use `Self._printChanges()` during debugging to identify unexpected redraws
- Profile on real devices in Release mode

### NEVER
- Use `id(UUID())` or any value that changes every render
- Use `AnyView` unless absolutely necessary
- Put conditional (`if`/`else`) content inside `ForEach` within `List`
- Create views with expensive initializers—defer work to `task` or `onAppear`

### PREFER INERT MODIFIERS FOR CONDITIONAL BEHAVIOR
```swift
// GOOD: maintains view identity
MyView()
    .opacity(isVisible ? 1 : 0)
    .disabled(!isEnabled)
    .blur(radius: isBlurred ? 10 : 0)

// AVOID: changes view identity
if isVisible {
    MyView()
} else {
    EmptyView()
}
```

### DEPENDENCY REDUCTION
```swift
// GOOD: pass only what's needed
struct UserAvatar: View {
    let imageURL: URL?
    let size: CGFloat
}

// AVOID: passing entire model
struct UserAvatar: View {
    let user: User  // View rebuilds if ANY user property changes
}
```

---

## Testing

### ALWAYS
- Use Swift Testing (`@Test`, `#expect`, `#require`) for new unit tests
- Extract business logic from views into testable ViewModels/services
- Use protocol-based dependency injection for mockability
- Use accessibility identifiers for UI tests
- Test ViewModels synchronously where possible; use `await` for async

### NEVER
- Test view body directly—test the logic that drives the view
- Use XCTest for new unit tests (use for UI tests and performance tests only)
- Match UI elements by text in UI tests—use accessibility identifiers

### PATTERNS
```swift
// Testable ViewModel with injected dependency
@Observable
@MainActor
final class ProfileViewModel {
    private let service: UserServiceProtocol
    var user: User?
    
    init(service: UserServiceProtocol = UserService()) {
        self.service = service
    }
    
    func load() async {
        user = try? await service.fetchUser()
    }
}

// Test
@Test("Profile loads user successfully")
func profileLoads() async {
    let mock = MockUserService(userToReturn: .fixture)
    let vm = ProfileViewModel(service: mock)
    
    await vm.load()
    
    #expect(vm.user?.name == "Test")
}
```

---

## Project Structure

### ALWAYS
- Organize by feature for medium-to-large projects
- Use Swift Package Manager for modularization when app grows
- Keep views thin—delegate logic to ViewModels
- Use constructor injection for ViewModels, environment for app-wide services

### RECOMMENDED STRUCTURE
```
App/
├── App.swift
├── Features/
│   ├── Authentication/
│   │   ├── Views/
│   │   ├── ViewModels/
│   │   ├── Models/
│   │   └── Services/
│   ├── Profile/
│   └── Home/
├── Core/
│   ├── Network/
│   ├── Extensions/
│   └── Utilities/
└── Shared/
    ├── Components/
    └── Styles/
```

---

## Code Style

### ALWAYS
- Use trailing closure syntax for the last closure parameter
- Use `guard` for early exits
- Prefer `let` over `var`
- Use meaningful names; avoid abbreviations except well-known ones (URL, ID)
- Mark classes as `final` unless designed for inheritance

### VIEW BODY GUIDELINES
- Keep `body` focused—extract complex subviews into computed properties or separate views
- Extract repeated view code into reusable components
- Use `ViewBuilder` functions for conditional view logic
- Limit `body` to ~30 lines; refactor if longer

```swift
struct ComplexView: View {
    var body: some View {
        VStack {
            headerSection
            contentSection
            footerSection
        }
    }
    
    private var headerSection: some View {
        // ...
    }
    
    @ViewBuilder
    private var contentSection: some View {
        if let data = viewModel.data {
            DataView(data: data)
        } else {
            PlaceholderView()
        }
    }
}
```

---

## Quick Reference: Deprecated → Modern

| Deprecated | Modern Replacement |
|------------|-------------------|
| `ObservableObject` | `@Observable` |
| `@Published` | (automatic with @Observable) |
| `@StateObject` | `@State` (for @Observable) |
| `@ObservedObject` | `@Bindable` or direct reference |
| `@EnvironmentObject` | `@Environment(Type.self)` |
| `NavigationView` | `NavigationStack` |
| `NavigationLink(destination:)` | `NavigationLink(value:)` + `navigationDestination` |
| `DispatchQueue.main.async` | `@MainActor` / `MainActor.run` |
| Completion handlers | `async/await` |
| `XCTestCase` (unit tests) | `@Test` with Swift Testing |


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

### ToolbarSpacer for Visual Grouping (macOS 26 / iOS 26)

In Liquid Glass, toolbar items with the same placement are automatically grouped into a single glass "bubble". To create visually separate groups while keeping items in the same area, use `ToolbarSpacer`:

```swift
.toolbar {
    // First group - document actions
    ToolbarItemGroup(placement: .primaryAction) {
        Button("Edit", systemImage: "pencil") { }
        Button("Share", systemImage: "square.and.arrow.up") { }
    }

    // Spacer creates visual separation between groups
    ToolbarSpacer(.fixed)

    // Second group - separate glass bubble
    ToolbarItemGroup(placement: .primaryAction) {
        Button("Sidebar", systemImage: "sidebar.right") { }
    }
}
```

**ToolbarSpacer options:**
- `.fixed` - Small fixed spacing, creates separate glass bubbles
- `.flexible` - Flexible spacing that pushes groups apart

Without `ToolbarSpacer`, multiple `ToolbarItemGroup` blocks with the same placement will merge into a single glass bubble. Different placements (e.g., `.primaryAction` vs `.secondaryAction`) create separation but position items in different areas of the toolbar.

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

### AppEnum Conformance with Swift 6 MainActor Isolation

When using `default-isolation=MainActor` (Xcode 26+), types defined in files with `@MainActor` classes inherit MainActor isolation. Extending such types to conform to `AppEnum` causes errors because `AppEnum` requires `Sendable` conformance.

**Problem:**
```swift
// In a file with @MainActor ViewModel class
public enum TimeFilter: String, CaseIterable {
    case today, thisWeek, all

    public var startDate: Date? { /* ... */ }
}

// This fails: "main actor-isolated conformance cannot satisfy Sendable requirement"
extension TimeFilter: AppEnum {
    static var typeDisplayRepresentation = TypeDisplayRepresentation(name: "Filter")
    static var caseDisplayRepresentations: [TimeFilter: DisplayRepresentation] = [:]
}
```

**Solution:** Add `Sendable` conformance and use `nonisolated` for both the enum properties and the `AppEnum` extension:

```swift
// 1. Make the enum Sendable and mark computed properties as nonisolated
public enum TimeFilter: String, CaseIterable, Sendable {
    case today, thisWeek, all

    nonisolated public var startDate: Date? {
        // Calendar operations are safe to call from any context
        let calendar = Calendar.current
        switch self {
        case .today: return calendar.startOfDay(for: Date())
        case .thisWeek: return calendar.dateInterval(of: .weekOfYear, for: Date())?.start
        case .all: return nil
        }
    }
}

// 2. Use nonisolated computed properties in the AppEnum extension
extension TimeFilter: @retroactive AppEnum {
    nonisolated public static var typeDisplayRepresentation: TypeDisplayRepresentation {
        TypeDisplayRepresentation(name: "Time Filter")
    }

    nonisolated public static var caseDisplayRepresentations: [TimeFilter: DisplayRepresentation] {
        [.today: "Today", .thisWeek: "This Week", .all: "All Time"]
    }
}
```

**Key Points:**
- Add `Sendable` to the enum declaration (safe for enums with no associated values or only `Sendable` associated values)
- Mark computed properties as `nonisolated` if they don't access actor-isolated state
- Use `@retroactive` when conforming to a protocol from another module in an extension
- Use computed properties (not stored) for `AppEnum` requirements to allow `nonisolated`

### Returning Files from App Intents

To return file data (images, documents) from an App Intent for use in Shortcuts, use `IntentFile`:

```swift
import UniformTypeIdentifiers

struct ExportImageIntent: AppIntent {
    static var title: LocalizedStringResource = "Export Image"

    @MainActor
    func perform() async throws -> some IntentResult & ReturnsValue<IntentFile> {
        // Generate image data
        guard let pngData = image.pngData else {
            throw ExportError.encodingFailed
        }

        // Create IntentFile with data, filename, and UTType
        let file = IntentFile(
            data: pngData,
            filename: "export-\(Date().formatted(.iso8601)).png",
            type: .png
        )

        return .result(value: file)
    }
}
```

**Key Points:**
- Import `UniformTypeIdentifiers` for `.png`, `.jpeg`, `.pdf`, etc.
- `IntentFile` can be saved, shared, or passed to other Shortcuts actions
- Use descriptive filenames - Shortcuts shows the filename to users
- The `type` parameter helps Shortcuts understand how to handle the file

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

## WidgetKit

### Widget Extension Architecture

Widgets run in a separate extension process with strict constraints:
- ~30MB memory limit
- No direct access to main app's SwiftData/CloudKit (different sandbox)
- Cannot display interactive UI elements (text fields, buttons that run code)
- Can only deep link to the app or trigger background App Intents

**Basic Widget Structure:**

```swift
// 1. Widget definition
struct MyWidget: Widget {
    let kind = "com.example.mywidget"  // Unique identifier

    var body: some WidgetConfiguration {
        AppIntentConfiguration(
            kind: kind,
            intent: MyWidgetIntent.self,
            provider: MyProvider()
        ) { entry in
            MyWidgetView(entry: entry)
        }
        .configurationDisplayName("My Widget")
        .description("Description shown in widget gallery")
        .supportedFamilies([.systemSmall])  // Limit to small size
    }
}

// 2. Widget bundle (entry point)
@main
struct MyWidgets: WidgetBundle {
    var body: some Widget {
        MyWidget()
        AnotherWidget()
    }
}
```

### Timeline Providers

Use `AppIntentTimelineProvider` for configurable widgets:

```swift
struct MyEntry: TimelineEntry {
    let date: Date
    let icon: WidgetIcon
    let color: WidgetColor
}

struct MyProvider: AppIntentTimelineProvider {
    // Shown in widget gallery before configuration
    func placeholder(in context: Context) -> MyEntry {
        MyEntry(date: .now, icon: .star, color: .blue)
    }

    // Shown during widget preview
    func snapshot(for configuration: MyWidgetIntent, in context: Context) async -> MyEntry {
        MyEntry(date: .now, icon: configuration.icon, color: configuration.color)
    }

    // Actual widget content - use .never policy for static widgets
    func timeline(for configuration: MyWidgetIntent, in context: Context) async -> Timeline<MyEntry> {
        let entry = MyEntry(date: .now, icon: configuration.icon, color: configuration.color)
        return Timeline(entries: [entry], policy: .never)
    }
}
```

### Widget Configuration with App Intents

Use `WidgetConfigurationIntent` for widget settings:

```swift
struct MyWidgetIntent: WidgetConfigurationIntent {
    static var title: LocalizedStringResource = "Configure Widget"
    static var description = IntentDescription("Customize widget appearance")

    @Parameter(title: "Icon", default: .star)
    var icon: WidgetIcon

    @Parameter(title: "Color", default: .blue)
    var color: WidgetColor

    // Simplified summary - WidgetKit shows parameters automatically
    static var parameterSummary: some ParameterSummary {
        Summary("Configure widget appearance")
    }
}
```

**Parameter Best Practices:**
- Use spatial titles for grid layouts: "Top Left: Icon" instead of "Button 1 Icon"
- Add descriptions to clarify behavior: `@Parameter(title: "Tag", description: "Set a tag to preset it, or leave empty")`
- Derive behavior from parameters when possible (e.g., mode from tag presence) to reduce parameter count

### Widget Views and Deep Linking

Widgets cannot run code on tap - they can only open URLs:

```swift
struct MyWidgetView: View {
    let entry: MyEntry

    var body: some View {
        VStack {
            Image(systemName: entry.icon.rawValue)
                .foregroundStyle(entry.color.swiftUIColor)
            Text("Tap to add")
        }
        .containerBackground(for: .widget) {
            Color.clear  // Let iOS 26 Liquid Glass show through
        }
        .widgetURL(entry.deepLinkURL)  // Single tap target for entire widget
        .accessibilityLabel("Add item")
    }
}
```

**Multiple Tap Targets:** Use `Link` views instead of `widgetURL` when you need multiple tap targets:

```swift
// widgetURL only works for single tap target
// Use Link for multiple independent tap targets (e.g., 2x2 button grid)
Grid {
    GridRow {
        Link(destination: url1) { Button1View() }
        Link(destination: url2) { Button2View() }
    }
}
// No .widgetURL() when using Link views
```

### Deep Link URL Handling

Generate URLs in the widget, parse them in the main app:

```swift
// In widget extension - generate URL
var deepLinkURL: URL {
    var components = URLComponents()
    components.scheme = "myapp"
    components.host = "action"
    components.queryItems = [
        URLQueryItem(name: "type", value: "quick"),
        URLQueryItem(name: "tag", value: tagName)
    ]
    // Safe fallback - hardcoded URL is known-valid
    return components.url ?? URL(string: "myapp://action?type=quick")!
}

// In main app - parse URL
struct QuickInputState {
    enum InputType: String { case quick, tagged }
    let type: InputType
    let presetTag: String?

    static func from(url: URL) -> QuickInputState? {
        guard url.scheme == "myapp", url.host == "action" else { return nil }
        let components = URLComponents(url: url, resolvingAgainstBaseURL: false)
        let queryItems = components?.queryItems ?? []

        guard let typeString = queryItems.first(where: { $0.name == "type" })?.value,
              let type = InputType(rawValue: typeString) else { return nil }

        let tag = queryItems.first(where: { $0.name == "tag" })?.value
        return QuickInputState(type: type, presetTag: tag)
    }
}

// In app entry point - handle URL
@main
struct MyApp: App {
    @State private var quickInputState: QuickInputState?

    var body: some Scene {
        WindowGroup {
            ContentView()
                .sheet(item: $quickInputState) { state in
                    QuickInputSheet(state: state)
                }
        }
        .handlesExternalEvents(matching: ["*"])
        .onOpenURL { url in
            if let state = QuickInputState.from(url: url) {
                quickInputState = state
            }
        }
    }
}
```

### Sharing Data with Widget Extension

Widget extensions cannot access the main app's SwiftData/CloudKit directly. Use App Group UserDefaults for simple data:

```swift
// In main app - update cache when data changes
enum WidgetTagCache {
    private static let cacheKey = "cachedWidgetTags"
    private static let appGroupID = "group.com.example.app"

    static func updateCache(tags: [String]) {
        guard let defaults = UserDefaults(suiteName: appGroupID) else { return }
        defaults.set(tags, forKey: cacheKey)
    }
}

// In widget extension - read from cache
struct TagEntityQuery: EntityQuery {
    private static let cacheKey = "cachedWidgetTags"
    private static let appGroupID = "group.com.example.app"

    func suggestedEntities() async throws -> [TagEntity] {
        guard let defaults = UserDefaults(suiteName: Self.appGroupID),
              let cached = defaults.stringArray(forKey: Self.cacheKey) else {
            return [TagEntity.noTagsPlaceholder]  // Show helpful message
        }
        return cached.map { TagEntity(id: $0) }
    }
}
```

### AppEntity for Dynamic Pickers

Use `AppEntity` with `EntityQuery` for dynamic configuration options:

```swift
struct TagEntity: AppEntity {
    static var typeDisplayRepresentation = TypeDisplayRepresentation(name: "Tag")
    static var defaultQuery = TagEntityQuery()

    var id: String
    var displayRepresentation: DisplayRepresentation {
        // Show helpful message for placeholder
        if id == "__no_tags__" {
            return DisplayRepresentation(title: "Create tags in the app first")
        }
        return DisplayRepresentation(title: "\(id)")
    }

    static let noTagsPlaceholder = TagEntity(id: "__no_tags__")

    var isPlaceholder: Bool { id == "__no_tags__" }
}

struct TagEntityQuery: EntityQuery {
    func entities(for identifiers: [String]) async throws -> [TagEntity] {
        identifiers.map { TagEntity(id: $0) }
    }

    func suggestedEntities() async throws -> [TagEntity] {
        let cached = getCachedTags() ?? []
        if cached.isEmpty {
            return [TagEntity.noTagsPlaceholder]
        }
        return cached.map { TagEntity(id: $0) }
    }
}
```

### iOS 26 Widget Styling

Use `containerBackground(for:)` with `Color.clear` to let Liquid Glass show through:

```swift
var body: some View {
    VStack { /* content */ }
        .containerBackground(for: .widget) {
            Color.clear  // Enables system glass effect
        }
}
```

Do NOT use:
- `widgetBackground()` (deprecated)
- Solid background colors (blocks glass effect)
- Custom materials on the container

### Common Widget Pitfalls

**Memory limits:** Widget extensions have ~30MB limit. Don't fetch large datasets:
```swift
// Bad - may exceed memory
let allSnippets = try modelContext.fetch(FetchDescriptor<Snippet>())

// Good - fetch from cached data or limit results
let cached = getCachedTags() ?? []
```

**No SwiftData in widgets:** CloudKit/SwiftData requires entitlements the widget extension doesn't have. Use App Group UserDefaults cache instead.

**No interactive UI:** Widgets can't have text fields, toggles, or buttons that run code. They can only:
- Open the app via URL (`widgetURL` or `Link`)
- Trigger background App Intents (`Button(intent:)` for non-UI work)

**Derived vs explicit parameters:** Reduce configuration complexity by deriving values:
```swift
// Instead of separate mode + tag parameters:
var isTagged: Bool { tag != nil && !tag!.isEmpty }
var typeString: String { isTagged ? "tagged" : "quick" }
```

**Aggressive widget extension caching (macOS):** macOS aggressively caches widget extension binaries. After rebuilding a widget extension, the system may continue running the old cached binary even after:
- Clean builds
- Running the main app from Xcode
- Removing and re-adding the widget

To force the new widget extension code to load:
1. Remove the widget from the desktop
2. Quit the main app
3. Kill widget-related processes: `killall chronod; killall NotificationCenter`
4. Run the app from Xcode
5. Add the widget fresh from the widget gallery

If that doesn't work, restart macOS to fully clear cached widget binaries. This is especially important when debugging widget extension code - your changes may not take effect until the cache is cleared.

## Code Sharing Between Targets

### Never Copy Files Between Targets

**Anti-pattern:** Copying source files between targets (e.g., from main app to widget extension) creates maintenance nightmares:
- Changes must be made in multiple places
- Files drift out of sync
- Build errors occur when one copy is updated but not others

**Correct approach:** Use a local Swift Package to share code:

```
MyProject/
├── MyApp/
├── MyWidget/
├── Packages/
│   └── MyCore/
│       ├── Package.swift
│       └── Sources/
│           └── MyCore/
│               ├── Models/
│               ├── Services/
│               └── Intents/
└── MyProject.xcodeproj
```

**Package.swift for shared code:**
```swift
// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "MyCore",
    platforms: [.iOS(.v18), .macOS(.v15)],
    products: [
        .library(name: "MyCore", targets: ["MyCore"])
    ],
    targets: [
        .target(
            name: "MyCore",
            swiftSettings: [.swiftLanguageMode(.v5)]  // Avoid Swift 6 concurrency issues
        )
    ]
)
```

**Adding to Xcode project:**
1. File → Add Package Dependencies → Add Local
2. Select the package folder
3. Add the package product to all targets that need it (main app, widget, tests)

**Making types available:**
- Mark shared types as `public`
- Add `public init()` to all types that need construction from outside the package
- Import the package in files that use it: `import MyCore`

### What to Share vs Keep Separate

**Share in package:**
- Models (SwiftData `@Model` classes)
- App Intents (for widget `Button(intent:)` to work)
- Services used by both app and extensions
- Utility types and extensions

**Keep in main app:**
- Views and ViewModels (UI layer)
- App-specific formatters and helpers
- Configuration files

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
