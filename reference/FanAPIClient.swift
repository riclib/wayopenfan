import Foundation

struct Fan: Codable, Identifiable {
    let id = UUID()
    let name: String
    let url: String
    
    enum CodingKeys: String, CodingKey {
        case name, url
    }
}

struct FanStatus: Codable {
    let status: String
    let rpm: Int
    let pwmPercent: Int
    
    enum CodingKeys: String, CodingKey {
        case status
        case rpm
        case pwmPercent = "pwm_percent"
    }
}

struct APIResponse: Codable {
    let status: String
    let message: String?
}

class FanAPIClient {
    private let session: URLSession
    
    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 5
        config.timeoutIntervalForResource = 5
        self.session = URLSession(configuration: config)
    }
    
    func getStatus(for fan: Fan) async throws -> FanStatus {
        let url = URL(string: "\(fan.url)/api/v0/fan/status")!
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw FanAPIError.invalidResponse
        }
        
        let status = try JSONDecoder().decode(FanStatus.self, from: data)
        
        guard status.status == "ok" else {
            throw FanAPIError.apiError(status.status)
        }
        
        return status
    }
    
    func setSpeed(for fan: Fan, speed: Int) async throws {
        let url = URL(string: "\(fan.url)/api/v0/fan/0/set?value=\(speed)")!
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw FanAPIError.invalidResponse
        }
        
        let apiResponse = try JSONDecoder().decode(APIResponse.self, from: data)
        
        guard apiResponse.status == "ok" else {
            throw FanAPIError.apiError(apiResponse.message ?? "Unknown error")
        }
    }
}

enum FanAPIError: LocalizedError {
    case invalidResponse
    case apiError(String)
    
    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid response from fan"
        case .apiError(let message):
            return "API Error: \(message)"
        }
    }
}