# Arjen's iOS Style Guide

A personal reference for building iOS 26+ / iPadOS 26+ / macOS 26+ apps in SwiftUI. Distilled from three working projects:

- **Prism** — read-only markdown viewer (single-document, content-rendering, lots of WKWebView work)
- **Transit** — kanban task tracker (multi-window, SwiftData + CloudKit, App Intents, MCP server)
- **Flux** — battery monitoring app (data-heavy dashboard, charts, networking, widgets)

Where the three projects agree, the convention is strong. Where they disagree, both options are listed with the trade-off. Apple Human Interface Guidelines fill any remaining gaps; references are noted by name where relevant.

---

## 1. Platform Baseline

- **Target iOS/iPadOS/macOS 26+ exclusively.** No backwards compatibility shims. The build settings are clean and the language is current.
- **Swift 6.2** with strict concurrency. Set `SWIFT_DEFAULT_ACTOR_ISOLATION = MainActor` (Transit's default) — every type is `@MainActor` unless explicitly opted out. This makes most SwiftUI code "just work" with strict concurrency.
- **SwiftUI only.** No UIKit/AppKit unless wrapping a system component (e.g. `WKWebView`, `NSWindow` host).
- **Xcode File System Sync** — keep it on. Don't hand-edit `pbxproj`.
- **Makefile-driven dev loop.** Every project has the same target set: `build`, `build-ios`, `build-macos`, `test-quick`, `test`, `test-ui`, `lint`, `lint-fix`, `clean`. Don't memorise `xcodebuild` — wrap it.
- **SwiftLint runs on every build.** Fix warnings, don't suppress them.

---

## 2. Project Layout

```
ProjectName/
├── ProjectName.xcodeproj
├── ProjectName/
│   ├── App/                    # @main entry, document model, scenes
│   ├── Models/                 # value types, @Model classes, enums
│   ├── Services/               # @MainActor @Observable business logic
│   ├── ViewModels/             # only if a view has non-trivial state
│   ├── Views/                  # SwiftUI views
│   ├── Theme/                  # colour and typography abstraction
│   ├── Settings/               # AppSettings + SettingsView
│   ├── Intents/                # App Intents (where applicable)
│   └── Resources/              # bundled assets, JS, HTML templates
├── ProjectNameTests/
├── ProjectNameUITests/
├── specs/                      # one folder per feature
└── docs/agent-notes/           # implementation notes for future sessions
```

Specs live next to code, not in a wiki. Each feature gets `requirements.md`, `design.md`, `tasks.md`, `decision_log.md` (Enhanced Nygard ADR format).

---

## 3. Architecture: Services Hold Logic, Views Render

The cross-cutting rule: **views never own business logic, and services never know about views.**

```swift
@MainActor
@Observable
final class TaskService {
    private let modelContext: ModelContext
    private let allocator: DisplayIDAllocator

    enum Error: Swift.Error { case displayIDUnavailable, invalidStatus, … }

    func createTask(name: String, project: Project) async throws -> TransitTask { … }
}
```

- Services are `@MainActor @Observable final class` — `@Observable` (not `ObservableObject`) is the iOS 17+ default.
- **Each service exposes a typed `Error` enum.** No throwing raw `Error`. Errors carry enough detail to be translated into a UI message or an Intent response without inspection.
- **Inject services via `@Environment`.** Construct them once in the `@main` `App.init()` (Transit pattern: `TransitApp.swift:47-130`) and attach with `.environment(taskService)`. Views read with `@Environment(TaskService.self) private var tasks`.
- **Pure logic lives outside services.** `StatusEngine` in Transit is a struct with static methods — testable without instantiating anything (`Transit/Services/StatusEngine.swift:20-33`). If a function has no state, it's not a service.

When does a "session" or "coordinator" make sense instead of a service? When the state is **document-scoped or view-tree-scoped**, not app-global. Prism's `DocumentSession` and `DocumentLayoutCoordinator` own per-document parsing and per-layout sheet flags — they're created with `@State` in the layout view and disposed when the document closes.

---

## 4. State Management

| Scope | Mechanism |
|---|---|
| App-wide service | `@MainActor @Observable` + `.environment()` |
| Document/window-scoped state | `@Observable` coordinator created with `@State` |
| View-local UI state | `@State` directly |
| User preferences | `AppSettings` (one `@Observable` singleton) backed by `UserDefaults` |
| Persistent data | SwiftData `@Model` |
| Secrets | Keychain via a thin wrapper |

Avoid `@StateObject`/`@ObservedObject`/`@Published` — they're the legacy `ObservableObject` path. `@Observable` is shorter, faster, and integrates with strict concurrency.

**One-way data flow.** Use `private(set)` on view-model state so only the owner mutates it; views call methods. Flux's `DashboardViewModel.swift` is a good model.

---

## 5. Layout & Adaptivity

**Use size classes, not device idiom.** `horizontalSizeClass == .compact` covers iPhone portrait and iPad split-view; it's what you actually want most of the time. Idiom checks (`UIDevice.current.userInterfaceIdiom`) get split-view wrong.

### The two-shell pattern (Prism)

For complex layouts that diverge significantly between compact and regular, split the shell:

```
DocumentReaderView         # picks the shell based on size class
├── CompactDocumentLayout  # iPhone shell (sheets, single column)
└── RegularDocumentLayout  # iPad/macOS shell (sidebars, split view)
```

Both shells share:
- A `DocumentLayoutCoordinator` (`@Observable`, `@State` in each shell) holding cross-cutting state
- A `SharedBlockViews` namespace of `@ViewBuilder` static funcs for sheet/popover content
- The underlying parsed model — never duplicated

Don't try to make one view do both layouts via conditionals. The shells diverge enough (toolbar visibility on iPhone vs sidebar widths on iPad) that one branchy view becomes unreadable.

### The single-view-with-geometry pattern (Transit)

For simpler layouts, one view with `GeometryReader` and a `columnCount` computed property is fine. Transit's `DashboardView.swift:31-77` calculates 1/3/5 columns inline based on width and `verticalSizeClass`.

**Rule of thumb:** if the platform-specific code exceeds ~30% of a view, split shells. Otherwise inline it.

### Don't centre bidirectional ScrollViews on macOS

`ScrollView([.vertical, .horizontal])` on macOS centres its content rather than pinning top-left. Apply `.frame(minWidth:, minHeight:, alignment: .topLeading)` to the inner content. Only needed when both axes are enabled.

---

## 6. Liquid Glass

iOS 26 / macOS 26 introduced Liquid Glass. The design language emerges naturally from native containers — **don't manually slather glass on every view.**

### Where glass works
- Navigation chrome — toolbars, sidebars, tab bars get it for free
- Section containers — `.glassEffect(.regular, in: RoundedRectangle(cornerRadius: 16))` for a discrete grouped panel (Transit's `LiquidGlassSection.swift:24`)
- Material backdrops on popovers and sheets that overlay content — `.background(.regularMaterial)` on macOS popovers (Prism's `FootnotePopoverView.swift:61`, `NotePopover.swift:85`)
- Forms — a plain `Form` in iOS 26 already renders with glass; don't fight it (Flux's `SettingsView.swift:20`)
- Hero cards / data summary tiles — `.thinMaterial` in a rounded shape gives a clean Liquid Glass tile (Flux's `BatteryHeroView.swift:27`)

### Where glass doesn't work
- **Buttons inside content.** `.buttonStyle(.glass)` and `.buttonStyle(.glassProminent)` exist; reserve them for toolbar/control surfaces, not inline content actions. None of the three projects use them in body content.
- **Task cards / list rows.** Use shadow + theme background colour. Glass-on-glass when scrolled over a glass nav bar looks muddy.
- **Text-dense reading surfaces.** Prism deliberately uses opaque theme colours for the document body — glass over body text reduces contrast.

### The Transit rule

> "Glass is for the navigation/control layer only, not for content."

This is the strongest single guideline. If you're tempted to add glass to a content card, default to **theme colour + shadow** instead.

Apple HIG ("Materials") covers the trade-offs — glass costs contrast and adds visual noise in dense data views.

---

## 7. Theming

A theme system is three layers:

1. **An `enum` of theme cases** (`PrismTheme`, `AppTheme`) — `Codable`, `CaseIterable`, persisted in `AppSettings`.
2. **A protocol of semantic colour properties** (`ThemeColors` in Prism — 70+ properties named by purpose: `background`, `foreground`, `accent`, `mermaidCardBackground`, `noteBadgeForeground`, …). Properties are `nonisolated` so they're readable from any actor context.
3. **Concrete implementations per theme** (`PrismLightColors`, `RefractionColors`, …).

Inject via `@Environment(\.themeColors)`. Views never reference `Color.red` directly — they read `colors.error` or `colors.warningBackground`. This makes theme additions trivial.

### Two valid abstraction depths

- **Heavy** (Prism): protocol + 70 semantic properties. Worth it when there are 5+ themes and dense visual variety.
- **Light** (Transit): `ResolvedTheme` enum (`universal | light | dark`) propagated via Environment, colours computed inline per view (`BoardBackground.swift:42-91`). Worth it when there are 2-3 themes and most colours are derivative of system colours.

Pick based on the design — don't over-engineer for two themes.

### Custom colour storage

Persist colours as **hex strings**, not `Color` values. `Color` is `@MainActor`-isolated when bridged through `UIColor`/`NSColor`, which infects everything. Use `Color.resolve(in: EnvironmentValues())` to extract channels (Transit's `Color+Codable.swift:20-26`).

### Typography

- One `TypographyResolver` struct, computed from `AppSettings` on demand — **don't cache it** in a service. It needs to respond to live setting changes.
- Baseline sizes differ by platform: macOS body 15pt, iOS body 17pt (Dynamic Type "Large"). The system defaults are wrong for both.
- Use `Font.custom(name, size: x, relativeTo: .body)` on iOS so Dynamic Type still scales the user's chosen font (Prism `TypographyResolver.swift:92`). On macOS, use explicit size — Dynamic Type isn't a concept there.
- Map heading levels to text styles + weights: H1 → `.title.bold()`, H2 → `.title2.bold()`, H5 → `.subheadline.semibold()`. Don't invent your own scale.

---

## 8. Cross-Platform Code

The shared-code-with-platform-shells pattern (see §5) keeps `#if os(...)` confined to the layout boundary. For everything else:

- **`#if os(macOS)` / `#if os(iOS)`** at the smallest unit that diverges — a modifier, not a whole view.
- **Type aliases when wrapping platform types.** `typealias PlatformImage = UIImage` (iOS) vs `NSImage` (macOS) keeps call sites clean. Prism uses this in image rendering.
- **Separate files for fundamentally different containers.** `ImageDetailSheet.swift` (iOS sheet) and `ImageDetailWindow.swift` (macOS NSWindow host) share nothing structurally — split them.
- **Shared model + platform-specific view.** `ZoomableImageView` works on both; the host (sheet vs window) doesn't.
- **`@Environment(\.openWindow)`** is the macOS-only path for spawning windows. iOS falls back to sheets. Wrap the call site in `#if os(macOS)` and have an iOS branch using `.sheet(item:)`.

### Don't add Mac Catalyst to a SwiftUI app

When the app is SwiftUI from the start, native macOS gives you better window management, real menu bars, and keyboard shortcuts. Catalyst is a path for porting UIKit apps; skip it for greenfield.

---

## 9. Concurrency

### Default to `@MainActor`

With `SWIFT_DEFAULT_ACTOR_ISOLATION = MainActor`, every type is on the main actor. The exceptions worth knowing:

- **`@Model` (SwiftData) classes follow standard isolation, not `@MainActor`.** They can be touched off-main when sensible.
- **`Codable` on enums silently triggers `@MainActor` inference.** Avoid making throwaway helpers `Codable` unless they need to be.
- **`UIColor`/`NSColor` extensions become `@MainActor`.** Use `Color.resolve(in:)` instead.

### Background work

- **Actors for pooled resources.** Prism's `DiagramCache` is an `actor` — a content cache that doesn't need to live on main.
- **`AsyncSemaphore` for bounded concurrency.** One global semaphore per resource class:
  - Network: 6 concurrent (Prism `SharedConcurrency.swift`)
  - WebView pool: per-pool semaphore sized to pool capacity (Prism `WebViewPool.swift:94-95`) — *not* a global one
- **Per-token cancellation.** When a long-running task can be invalidated by a newer one (e.g. WebView navigation), assign a `UUID` token at start and check it before publishing results. Stale timeouts that fire after re-use will detect they no longer own the slot.

### Auto-refresh / live data (Flux pattern)

A reusable timer loop:

```swift
func startAutoRefresh() {
    guard refreshTask == nil else { return }
    refreshTask = Task {
        while !Task.isCancelled {
            await refresh()
            try? await sleep(for: interval)
        }
    }
}
```

- `.onAppear` starts it, `.onDisappear` cancels and nils the task.
- Observe `scenePhase` — pause on `.background`, resume on `.active`. Without this, you burn battery and re-poll networks while the app's hidden.
- Inject the `sleep` closure for testing — production passes `Task.sleep(for:)`, tests pass an immediate stub.

---

## 10. Networking

The Flux pattern is the reference: typed errors, no third-party libraries, clean separation.

```swift
final class URLSessionAPIClient: APIClient {
    init(baseURL: URL, keychainService: KeychainService) { … }   // production
    init(baseURL: URL, token: String) { … }                       // settings validation

    private func performRequest<T: Decodable>(…) async throws -> T {
        guard let token = tokenProvider(), !token.isEmpty else { throw .notConfigured }
        // Bearer auth, status code mapping, typed throw
    }
}
```

- **Two initialisers** if you need an "unauthenticated probe" path (validating a token before persisting). One reads from Keychain, one accepts an explicit token.
- **Map status codes to typed errors centrally.** 400 → parse `APIErrorResponse` and throw `.badRequest(detail)`. 401/403 → `.unauthorized`. 5xx → `.serverError`. Else → `.unexpectedStatus(Int)`.
- **`URLSession` with `.reloadIgnoringLocalCacheData`** for live data. The default disk cache is wrong for a polling client.
- **Errors expose a `.message` and `.suggestsSettings: Bool`.** The error enum tells the UI both what went wrong *and* what to do about it. Don't put that logic in views.
- **No third-party HTTP libraries.** `URLSession` + `Codable` is enough for everything any of these apps does.

### Keychain

- Custom thin wrapper around Security framework — ~150 lines, no dependency.
- Use `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly` (not `WhenUnlocked` — that breaks background fetches).
- Set `kSecAttrAccessGroup` to your App Group identifier so widgets share credentials (Flux `KeychainService.swift:42`).
- Save flow: delete first, then add. SecItem APIs don't have a clean upsert.

### Remote URL handling (Prism)

- 10 MB hard cap on download (streaming, fail fast on overflow).
- Ephemeral `URLSession` (no cookies, no cache persistence).
- Domain-specific URL transformers (e.g. GitHub blob URL → raw URL) live in dedicated services, not inline in the loader.

---

## 11. SwiftData + CloudKit

When you add CloudKit sync, SwiftData rules tighten:

- **All relationships must be optional.** CloudKit's eventual consistency requires it. The compiler doesn't enforce this, but sync silently breaks if you don't.
- **Delete rules: `.cascade` or `.nullify` only.** No `.deny`.
- **`@Model` inits take raw types, not SwiftUI types.** Store `colorHex: String`, not `color: Color`. SwiftUI types drag in actor isolation.
- **Schema migration via versioned schemas.** Bump the schema version on every model change, even small ones — CloudKit hates implicit migration.

### Display IDs separate from UUIDs

Both Transit and Prism's notes use a UUID for identity *and* a separate `permanentDisplayId: Int` for human-facing references (`T-42`, `M-3`). Allocate display IDs via a CloudKit counter record with optimistic locking, with a provisional fallback when offline. Promote provisional IDs on connectivity restore.

### Safe rollback

SwiftData's `rollback()` doesn't reliably re-fault `@Model` properties. Workaround (Transit `ModelContext+SafeRollback.swift:17`):

```swift
func safeRollback() {
    rollback()
    // Force re-fault by fetching all entity types
    _ = (try? fetch(FetchDescriptor<Project>())) ?? []
    _ = (try? fetch(FetchDescriptor<TransitTask>())) ?? []
    // …etc
}
```

**For object creation, prefer `delete()` over rollback on save failure** — rollback can leave the object in a partially-faulted state.

### Caching pattern (Flux)

When the app fetches network data and SwiftData caches it:

- Cache historical (immutable) data only. Don't cache today's mutable data — always fetch fresh.
- Use a natural key (date string `YYYY-MM-DD`) with `@Attribute(.unique)` for upsert semantics.
- On network failure, fall back to cached data with a "stale" indicator in the UI. Don't silently serve stale data.

---

## 12. Charts (Flux)

SwiftUI Charts is sufficient for any data view I've built; no third-party charting library is needed.

- Use `AreaMark` for filled trends, `RuleMark` for thresholds (with `.dash([4, 4])` for soft markers), `PointMark` for highlight annotations, `RectangleMark` for context bands (e.g. off-peak windows).
- **Selection via `chartXSelection(value: $selectedDate)`.** SwiftUI handles the gesture. Find the nearest data point in a computed property.
- **Cross-chart synchronisation:** a reusable `historySelectionOverlay` extension (Flux `ChartHighlightOverlay.swift`) attached to multiple charts shares a `@State selectedDate` so tapping any chart highlights the same point on all.
- Stride x-axis ticks meaningfully — `.stride(by: .hour, count: 3)` for a 24h view; never let SwiftUI pick.
- Pin y-axis domain explicitly when the data is bounded (`0...100` for percentage). Auto-scaling makes empty days look dramatic.

---

## 13. Sheets, Popovers, and Windows

Match the surface to the platform:

| Surface | iPhone | iPad | macOS |
|---|---|---|---|
| Quick action / form | `.sheet` | `.sheet` (mid detent) or popover | popover or sheet |
| Detail view | `.sheet` (full) | navigation push or sheet | new window (`openWindow`) |
| Confirmation | `.confirmationDialog` | same | same |
| Annotation/footnote | `.sheet(detents: [.medium])` | `.popover` | `.popover` with `.background(.regularMaterial)` |
| Image zoom / diagram | `.sheet` (full screen cover) | `.sheet` | new window |
| Settings | navigation push | navigation push | new window via `openWindow(id: "settings")` |

Rules:
- **iPhone gets sheets.** Don't try to fit popovers on phones.
- **macOS gets windows for anything substantial** — settings, image detail, diagram detail. Respect the platform.
- **iPad is the awkward middle.** Default to the same surface as iPhone unless the size class flips.
- **Don't use `.fullScreenCover` unless you're truly modal** (onboarding, lock screen). It bypasses the gesture-to-dismiss affordance users expect.

---

## 14. Drag-and-Drop (Transit)

Kanban drag is straightforward in modern SwiftUI:

```swift
TaskCardView(task: task)
    .draggable(task.id.uuidString)

ColumnView()
    .dropDestination(for: String.self) { ids, _ in
        guard let id = ids.first else { return false }
        return onDrop?(id) ?? false
    }
```

- Drag the UUID string, not the model. Models aren't `Codable` to the drag pasteboard.
- **Guard against same-column drops** at the handler level — the drop succeeds technically, but you don't want to mutate state.
- **Animate `isDropTargeted`** with `.withAnimation()` for visual feedback.
- Status transition logic stays in the service (`StatusEngine.applyTransition`), not in the drop handler.

---

## 15. App Intents (Transit)

The pattern that scales: **Intents take a JSON string in, return a JSON string out.**

```swift
struct CreateTaskIntent: AppIntent {
    @Parameter(title: "Input JSON") var input: String
    @Dependency var taskService: TaskService

    func perform() async throws -> some IntentResult & ReturnsValue<String> {
        let result = try await Self.execute(input: input, services: services)
        return .result(value: result)
    }
}
```

- **Errors are JSON-encoded into the result string**, not thrown out of the intent. Shortcuts displays errors badly; controlled JSON gives the caller a uniform shape.
- **Pure helpers in `IntentHelpers.swift`:** `parseJSON`, `encodeJSON`, error-mapping functions. `nonisolated` enum with static methods.
- **Visual intents** (`FindTasksIntent`, `AddTaskIntent` for Shortcuts UI) use `AppEntity` types instead of JSON. Reserve those for genuinely user-facing intents — programmatic callers should use the JSON variants.
- **`@Dependency`** for service injection. Set up the dependency container once in `App.init()`.

---

## 16. Widgets (Flux)

- `StaticConfiguration` + `TimelineProvider`. Don't reach for `IntentConfiguration` unless the user actually configures the widget.
- **Widgets share Keychain via App Group.** Widget extension target needs the same App Group entitlement as the app.
- **Snapshot caching.** When the app refreshes, write a small snapshot to a shared `UserDefaults(suiteName:)` and call `WidgetCenter.shared.reloadTimelines(ofKind:)`.
- **Debounce widget reloads.** Flux uses 5-minute minimum spacing — calling `reloadTimelines` more often is throttled by the system anyway, and excessive calls drain battery.

---

## 17. Accessibility

Not optional. Every commit should pass a baseline check.

- **`@Environment(\.accessibilityReduceMotion)`** — gate every animation. `reduceMotion ? nil : .easeInOut(duration: 0.2)`.
- **`accessibilityLabel`** on icon-only controls and any view with custom rendering (Prism's `MermaidPreviewCard.swift:100`: `.accessibilityLabel("\(diagramType) diagram")`).
- **Dynamic Type support on iOS** via `Font.custom(_, relativeTo:)`. Test with `Larger Text` enabled — don't ship a layout that breaks at "AX5".
- **VoiceOver focus order** — group cards into `.accessibilityElement(children: .combine)` when the natural order would be wrong.
- **`Reduce Transparency` and `Increase Contrast`** — glass effects degrade gracefully because of native containers; don't override.

Apple HIG's "Accessibility" section is the canonical reference and short.

---

## 18. Loading, Empty, and Error States

Three states every data view must handle, in this order of importance:

1. **Empty.** First-run, no data yet. Provide a one-line explanation and a primary action ("Open a file…", "Create your first task"). Never show a blank view.
2. **Error.** Show the error's `.message` (typed errors do this work for you). Provide a retry button. If `error.suggestsSettings == true`, deep-link to Settings.
3. **Loading.** Show a `ProgressView` only after a small delay (~200ms) to avoid flicker on cached data. **Stale-while-revalidate**: render cached content immediately, show a small banner if a refresh failed.

Don't conflate "no data" with "no internet" with "auth failure" — they need different messages and different actions.

---

## 19. Testing

- **`make test-quick` during development** — unit tests on macOS, no simulator. Fast iteration.
- **`make test` and `make test-ui` before pushing** — full simulator runs. Both must be green and warning-free.
- **`@MainActor` on test classes** when testing `@MainActor` types (which is most types).
- **Inject side-effecting closures.** Flux's `DashboardViewModel` takes `sleep` as a closure for fast tests. Same pattern for `Date.now`, network clients, etc.
- **No mocks for SwiftData.** Use an in-memory `ModelContainer` with the real schema. Mocking the persistence layer hides bugs the migration path will surface in production.
- **UI tests are for sheet states and gesture flows** — don't unit-test through the UI layer.

---

## 20. Decision Logs

Every feature in `specs/<feature>/` keeps a `decision_log.md` in Enhanced Nygard ADR format:

- Numbered, dated, status (proposed/accepted/rejected/superseded)
- **Context** — what problem
- **Decision** — what was decided (declarative, 1-3 sentences)
- **Rationale** — why
- **Alternatives Considered** — at least 2-3, each with rejection reason
- **Consequences** — both positive and negative

Read a few from each project (e.g. `specs/transit-v1/decision_log.md`, `specs/search/decision_log.md`) for the tone. The discipline pays off six months later when nobody remembers why a thing is the way it is.

**Update over rewrite.** When a decision is superseded, change the status to `superseded by Decision N` and add a new entry. Don't rewrite history.

---

## 21. Common Gotchas

A list of things that bit me in at least one of these projects:

- **WKWebView on macOS needs `com.apple.security.network.client` entitlement** even for purely local content. Without it, the WebContent process fails silently and rendering looks broken with no error. (Prism)
- **`.scrollDismissesKeyboard(.interactively)`** is iOS-only. Wrap in `#if os(iOS)`.
- **`NavigationSplitView(preferredCompactColumn:)`** + `onChange(of: selectedScreen) { navigationPath = NavigationPath() }` — without the reset, sidebar selection doesn't clear the pushed stack. (Flux)
- **`.searchable()`** on iOS auto-creates a search bar; on macOS it doesn't render unless the parent has a toolbar. Don't expect parity.
- **CloudKit relationships must be optional** (see §11). The compiler won't tell you.
- **`Codable` enums become `@MainActor`** under default-MainActor isolation. Be deliberate.
- **`ScrollView([.horizontal, .vertical])` on macOS centres content** — pin with `.frame(alignment: .topLeading)`.
- **SwiftData `rollback()` doesn't re-fault.** Use `safeRollback()` or delete-on-failure for creates. (Transit)
- **Mermaid/SVG WKWebView pools need per-navigation tokens** — without a UUID token, a stale timeout from a previous nav can fire and reset state on the current one. (Prism)
- **`.glassEffect()` over body text** kills contrast. Use opaque theme colours for reading surfaces.
- **`UIColor`/`NSColor` extensions infect actor isolation.** Resolve via `Color.resolve(in: EnvironmentValues())`.

---

## 22. What's Not in This Guide (Yet)

Areas these three projects haven't exercised, where I'd want more data before opinion-stating:

- **Universal links / deep linking** beyond `prism://` schemes
- **CarPlay / watchOS / visionOS**
- **Push notifications and APNs**
- **Background tasks** (`BGTaskScheduler`) beyond simple foreground refresh
- **In-app purchases / subscriptions**
- **Heavy animation / SpriteKit / RealityKit**

When one of those comes up, the section gets written from real practice, not from documentation.

---

## References

- Apple Human Interface Guidelines — particularly the "Materials", "Accessibility", "Layout", and "Navigation" sections.
- Apple's *Adopting Liquid Glass* documentation (WWDC 2025) for the glass design language.
- The three reference projects:
  - `/Users/arjen/projects/personal/prism`
  - `/Users/arjen/projects/personal/transit`
  - `/Users/arjen/projects/personal/flux`
- Project decision logs in each `specs/*/decision_log.md` — the live record of why each project diverges from this guide.
