import AppKit
import SwiftUI

enum Section: String, CaseIterable, Identifiable {
    case connect = "连接设备"
    case diagnosis = "布局诊断"
    case swipeTax = "滑动成本"
    case mirror = "屏幕镜像"
    case obituary = "告别旧布局"
    case transform = "重新整理"
    case apps = "iPhone 应用"

    var id: String { rawValue }
    var icon: String {
        switch self {
        case .connect: return "cable.connector"
        case .diagnosis: return "waveform.path.ecg"
        case .swipeTax: return "hand.draw"
        case .mirror: return "person.crop.rectangle"
        case .obituary: return "text.book.closed"
        case .transform: return "wand.and.stars"
        case .apps: return "square.grid.3x3.square"
        }
    }
}

@MainActor
final class AppModel: ObservableObject {
    @Published var section: Section = .connect
    @Published var busy = false
    @Published var connected = false
    @Published var demo = false
    @Published var deviceName = "未连接设备"
    @Published var headline = "让主屏幕重新服务于你的目标。"
    @Published var detail = "使用数据线连接已信任的 iPhone，或用安全的演示数据体验全部只读功能。"
    @Published var score: Int?
    @Published var metrics: [(String, Int)] = []
    @Published var recommendations: [String] = []
    @Published var categories: [(String, Int)] = []
    @Published var planID: String?
    @Published var beforePages: Int?
    @Published var afterPages: Int?
    @Published var error: String?
    @Published var selectedPreset = "focus"
    @Published var confirmApply = false

    func command(_ name: String, extra: [String] = []) {
        busy = true
        error = nil
        var arguments = [name]
        if demo { arguments.append("--demo") }
        arguments.append(contentsOf: extra)
        Backend.run(arguments) { [weak self] result in
            DispatchQueue.main.async {
                guard let self else { return }
                self.busy = false
                switch result {
                case .failure(let problem): self.error = problem.localizedDescription
                case .success(let json): self.consume(name, json)
                }
            }
        }
    }

    func startDemo() {
        demo = true
        connected = true
        deviceName = "演示 iPhone"
        command("diagnose")
        section = .diagnosis
    }

    func connect() {
        demo = false
        command("status")
    }

    func preview(_ preset: String) {
        command("preview", extra: ["--preset", preset])
    }

    func applyPlan() {
        guard let planID else { return }
        command("apply", extra: ["--plan", planID, "--confirm", "APPLY"])
    }

    private func consume(_ command: String, _ json: [String: Any]) {
        guard (json["ok"] as? Bool) == true else {
            error = json["error"] as? String ?? "设备服务返回了未知错误。"
            return
        }
        if let device = json["device"] as? [String: Any], let name = device["name"] as? String {
            deviceName = name
        }
        if command == "status" {
            let devices = json["devices"] as? [[String: Any]] ?? []
            connected = !devices.isEmpty
            deviceName = (devices.first?["name"] as? String) ?? (devices.first?["udid"] as? String) ?? "未连接设备"
            headline = connected ? "已找到设备，正在读取主屏幕。" : "没有检测到已配对的 USB 设备。"
            detail = connected ? "在生成预览并明确确认之前，手机布局不会改变。" : "请保持手机解锁；若出现提示，请点“信任此电脑”，并确认使用的是可传输数据的数据线。"
            if connected {
                section = .diagnosis
                self.command("diagnose")
            }
            return
        }
        if command == "apply" {
            headline = "新布局已应用"
            detail = "写入前已创建安全备份：\(json["backup"] as? String ?? "已保存")"
            return
        }
        if command == "preview" {
            planID = json["id"] as? String
            let before = json["before"] as? [String: Any]
            let after = json["after"] as? [String: Any]
            beforePages = (before?["counts"] as? [String: Any])?["pages"] as? Int
            afterPages = (after?["counts"] as? [String: Any])?["pages"] as? Int
            headline = "\(json["preset"] as? String ?? "新")方案已准备好"
            detail = json["warning"] as? String ?? "应用前请先检查预览。"
            return
        }
        guard let report = json["report"] as? [String: Any] else { return }
        if command == "diagnose" {
            score = report["score"] as? Int
            headline = report["archetype"] as? String ?? "你的布局"
            detail = report["summary"] as? String ?? ""
            let metricNames = ["efficiency": "页面效率", "foldering": "文件夹整理", "focus": "专注程度", "balance": "分类平衡"]
            metrics = ((report["metrics"] as? [String: Int]) ?? [:]).map { (metricNames[$0.key] ?? $0.key, $0.value) }.sorted { $0.0 < $1.0 }
            recommendations = report["recommendations"] as? [String] ?? []
            let categoryNames = ["Social": "社交", "Work": "工作", "Media": "影音", "Finance": "财务", "Health": "健康", "Travel": "出行", "Other": "其他"]
            categories = ((report["categories"] as? [String: Int]) ?? [:]).map { (categoryNames[$0.key] ?? $0.key, $0.value) }.sorted { $0.1 > $1.1 }
        } else if command == "swipe-tax" {
            let minutes = report["yearlyMinutes"] as? Int ?? 0
            headline = "每年大约浪费 \(minutes) 分钟"
            detail = "按每天打开应用 45 次，根据页面层级和文件夹深度估算。"
        } else {
            headline = report["headline"] as? String ?? report["title"] as? String ?? "屏幕观察"
            detail = report["body"] as? String ?? ""
        }
    }
}

enum Backend {
    static func run(_ arguments: [String], completion: @escaping (Result<[String: Any], Error>) -> Void) {
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                guard let resources = Bundle.main.resourceURL else { throw BackendError.resources }
                let python = resources.appendingPathComponent("python/bin/python3")
                let backend = resources.appendingPathComponent("backend")
                let process = Process()
                process.executableURL = python
                process.arguments = ["-m", "unjiggle_rebuilt"] + arguments
                process.environment = [
                    "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin",
                    "PYTHONPATH": backend.path,
                    "PYTHONUNBUFFERED": "1",
                ]
                let output = Pipe()
                process.standardOutput = output
                process.standardError = Pipe()
                try process.run()
                process.waitUntilExit()
                let data = output.fileHandleForReading.readDataToEndOfFile()
                guard let value = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw BackendError.invalidOutput }
                completion(.success(value))
            } catch {
                completion(.failure(error))
            }
        }
    }

    enum BackendError: LocalizedError {
        case resources, invalidOutput
        var errorDescription: String? {
            switch self {
            case .resources: return "应用资源不完整。"
            case .invalidOutput: return "设备服务返回了无法解析的数据。"
            }
        }
    }
}

struct RootView: View {
    @StateObject private var model = AppModel()

    var body: some View {
        NavigationSplitView {
            List(Section.allCases, selection: $model.section) { item in
                Label(item.rawValue, systemImage: item.icon).tag(item)
            }
            .navigationTitle("理屏")
            .safeAreaInset(edge: .bottom) {
                HStack(spacing: 8) {
                    Circle().fill(model.connected ? Color.green : Color.secondary).frame(width: 8, height: 8)
                    Text(model.deviceName).font(.caption).lineLimit(1)
                }.padding(12).frame(maxWidth: .infinity, alignment: .leading)
            }
            .navigationSplitViewColumnWidth(min: 210, ideal: 230)
        } detail: {
            ZStack {
                LinearGradient(colors: [Color(nsColor: .windowBackgroundColor), Color.accentColor.opacity(0.06)], startPoint: .top, endPoint: .bottom)
                    .ignoresSafeArea()
                ScrollView {
                    VStack(alignment: .leading, spacing: 24) {
                        header
                        content
                    }.padding(42).frame(maxWidth: 850, alignment: .leading)
                }
                if model.busy { ProgressView().controlSize(.large).padding(22).background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16)) }
            }
            .alert("操作未完成", isPresented: Binding(get: { model.error != nil }, set: { if !$0 { model.error = nil } })) {
                Button("知道了") { model.error = nil }
            } message: { Text(model.error ?? "") }
            .alert("确定应用这个布局？", isPresented: $model.confirmApply) {
                Button("取消", role: .cancel) {}
                Button("应用", role: .destructive) { model.applyPlan() }
            } message: { Text("应用会再次核对当前布局、先创建备份，然后才把预览方案发送到手机。") }
        }
        .frame(minWidth: 980, minHeight: 680)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(model.section.rawValue).font(.caption.weight(.semibold)).foregroundStyle(.secondary)
            Text(model.headline).font(.system(size: 34, weight: .bold, design: .rounded))
            Text(model.detail).font(.title3).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
        }
    }

    @ViewBuilder private var content: some View {
        switch model.section {
        case .connect:
            featureCard("所有分析都在本机完成", "不需要账号、订阅或许可证服务器，也不会上传你的应用列表。") {
                HStack {
                    Button("连接 USB 设备") { model.connect() }.buttonStyle(.borderedProminent)
                    Button("体验演示模式") { model.startDemo() }.buttonStyle(.bordered)
                }
            }
        case .diagnosis:
            HStack(alignment: .top, spacing: 18) {
                if let score = model.score { scoreCard(score) }
                VStack(alignment: .leading, spacing: 12) {
                    ForEach(model.metrics, id: \.0) { name, value in
                        VStack(alignment: .leading) {
                            HStack { Text(name); Spacer(); Text("\(value)") }
                            ProgressView(value: Double(value), total: 100)
                        }
                    }
                }.padding(22).background(.regularMaterial, in: RoundedRectangle(cornerRadius: 18))
            }
            actionButton("重新诊断", command: "diagnose")
            ForEach(model.recommendations, id: \.self) { recommendation in Label(recommendation, systemImage: "lightbulb") }
        case .swipeTax:
            featureCard("估算寻找应用的时间成本", "根据页面层级、文件夹深度和每日打开次数进行估算，不会读取“屏幕使用时间”。") {
                actionButton("计算滑动成本", command: "swipe-tax")
            }
        case .mirror:
            featureCard("从布局看使用习惯", "根据当前布局在本地生成一段观察，不调用云端 AI，也不需要 API 密钥。") {
                actionButton("生成屏幕观察", command: "mirror")
            }
        case .obituary:
            featureCard("和旧布局好好告别", "在真正整理之前，为当前布局生成一段轻松的本地总结。") {
                actionButton("生成告别文", command: "obituary")
            }
        case .transform:
            Picker("整理方案", selection: $model.selectedPreset) {
                Text("专注").tag("focus")
                Text("放松").tag("relax")
                Text("极简").tag("minimal")
                Text("美观").tag("beautiful")
            }.pickerStyle(.segmented)
            Button("生成布局预览") { model.preview(model.selectedPreset) }.buttonStyle(.borderedProminent)
            if let before = model.beforePages, let after = model.afterPages {
                featureCard("\(before) 页 → \(after) 页", "预览编号：\(model.planID ?? "—")。写入前会再次核对手机上的当前布局。") {
                    Button("应用这个预览") { model.confirmApply = true }
                        .buttonStyle(.borderedProminent).tint(.orange).disabled(model.demo)
                    if model.demo { Text("演示模式不会写入设备。").foregroundStyle(.secondary) }
                }
            }
        case .apps:
            featureCard("应用分类清单", "扫描当前布局，使用透明的本地规则统计各类应用数量。") {
                actionButton("扫描应用", command: "diagnose")
            }
            ForEach(model.categories, id: \.0) { name, count in
                HStack { Text(name); Spacer(); Text("\(count)").foregroundStyle(.secondary) }
                    .padding(.vertical, 4)
            }
        }
    }

    private func actionButton(_ title: String, command: String) -> some View {
        Button(title) {
            if model.connected {
                model.command(command)
            } else {
                model.error = "请先在“连接设备”页面连接 iPhone，或主动进入演示模式。"
            }
        }.buttonStyle(.borderedProminent)
    }

    private func scoreCard(_ score: Int) -> some View {
        VStack { Text("\(score)").font(.system(size: 64, weight: .bold, design: .rounded)); Text("布局评分").foregroundStyle(.secondary) }
            .frame(width: 180, height: 160).background(Color.accentColor.opacity(0.12), in: RoundedRectangle(cornerRadius: 18))
    }

    private func featureCard<Content: View>(_ title: String, _ body: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(title).font(.title2.weight(.semibold))
            Text(body).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            content()
        }.padding(24).frame(maxWidth: .infinity, alignment: .leading).background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20))
    }
}

@main
struct UnjiggleRebuiltApp: App {
    var body: some Scene {
        WindowGroup { RootView() }
            .windowStyle(.titleBar)
            .defaultSize(width: 1120, height: 760)
        Settings { Text("理屏（本地重制版）0.2.2").padding(30) }
    }
}
