#!/usr/bin/env swift

import Foundation
func readEnv(_ key: String) -> String? {
    let value = ProcessInfo.processInfo.environment[key]?.trimmingCharacters(in: .whitespacesAndNewlines)
    return value?.isEmpty == false ? value : nil
}
struct UsageData {
    let fiveHourUtil: Int
    let fiveHourResets: String?
    let dailyUtil: Int?
    let dailyResets: String?
}

func fetchUsageData(sessionKey: String, orgId: String) async throws -> UsageData {
    // Build URL safely - validate orgId doesn't contain path traversal
    guard !orgId.contains(".."), !orgId.contains("/") else {
        throw NSError(domain: "ClaudeAPI", code: 5, userInfo: [NSLocalizedDescriptionKey: "Invalid organization ID"])
    }

    guard let url = URL(string: "https://claude.ai/api/organizations/\(orgId)/usage") else {
        throw NSError(domain: "ClaudeAPI", code: 0, userInfo: [NSLocalizedDescriptionKey: "Invalid URL"])
    }

    var request = URLRequest(url: url)
    request.setValue("sessionKey=\(sessionKey)", forHTTPHeaderField: "Cookie")
    request.setValue("application/json", forHTTPHeaderField: "Accept")
    request.httpMethod = "GET"

    let (data, response) = try await URLSession.shared.data(for: request)

    guard let httpResponse = response as? HTTPURLResponse,
          httpResponse.statusCode == 200 else {
        throw NSError(domain: "ClaudeAPI", code: 3, userInfo: [NSLocalizedDescriptionKey: "Failed to fetch usage"])
    }

    if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
       let fiveHour = json["five_hour"] as? [String: Any],
       let fiveHourUtil = fiveHour["utilization"] as? Int {
        let fiveHourResets = fiveHour["resets_at"] as? String

        var dailyUtil: Int? = nil
        var dailyResets: String? = nil
        if let sevenDay = json["seven_day"] as? [String: Any] {
            dailyUtil = sevenDay["utilization"] as? Int
            dailyResets = sevenDay["resets_at"] as? String
        }

        return UsageData(
            fiveHourUtil: fiveHourUtil,
            fiveHourResets: fiveHourResets,
            dailyUtil: dailyUtil,
            dailyResets: dailyResets
        )
    }

    throw NSError(domain: "ClaudeAPI", code: 4, userInfo: [NSLocalizedDescriptionKey: "Invalid response format"])
}

// Main execution
// Use Task to run async code, RunLoop keeps script alive until exit() is called
Task {
    guard let sessionKey = readEnv("CLAUDE_SESSION_KEY") else {
        print("ERROR:NO_SESSION_KEY")
        exit(1)
    }

    guard let orgId = readEnv("CLAUDE_ORG_ID") else {
        print("ERROR:NO_ORG_CONFIGURED")
        exit(1)
    }

    do {
        let usage = try await fetchUsageData(sessionKey: sessionKey, orgId: orgId)

        // Output format: 5H_UTIL|5H_RESETS|DAILY_UTIL|DAILY_RESETS
        let fiveResets = usage.fiveHourResets ?? ""
        let dUtil = usage.dailyUtil.map { String($0) } ?? ""
        let dResets = usage.dailyResets ?? ""
        print("\(usage.fiveHourUtil)|\(fiveResets)|\(dUtil)|\(dResets)")
        exit(0)
    } catch {
        print("ERROR:\(error.localizedDescription)")
        exit(1)
    }
}

// Keep script alive while async Task executes
RunLoop.main.run()