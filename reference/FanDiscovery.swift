import Foundation
import Network

class FanDiscovery: NSObject {
    private var browser: NWBrowser?
    private var discoveredFans: [DiscoveredFan] = []
    var onFansDiscovered: (([DiscoveredFan]) -> Void)?
    
    struct DiscoveredFan {
        let name: String
        let hostname: String
        
        var url: String {
            return "http://\(hostname).local"
        }
    }
    
    override init() {
        super.init()
        setupBrowser()
    }
    
    private func setupBrowser() {
        let parameters = NWParameters()
        parameters.includePeerToPeer = true
        
        browser = NWBrowser(for: .bonjour(type: "_http._tcp", domain: nil), using: parameters)
        
        browser?.browseResultsChangedHandler = { [weak self] results, changes in
            self?.handleBrowseResults(results)
        }
        
        browser?.stateUpdateHandler = { state in
            switch state {
            case .ready:
                print("mDNS browser ready")
            case .failed(let error):
                print("mDNS browser failed: \(error)")
            default:
                break
            }
        }
    }
    
    func startDiscovery() {
        browser?.start(queue: .main)
    }
    
    func stopDiscovery() {
        browser?.cancel()
    }
    
    private func handleBrowseResults(_ results: Set<NWBrowser.Result>) {
        discoveredFans.removeAll()
        
        for result in results {
            if case let .service(name, _, _, _) = result.endpoint {
                // Check if the service name starts with "uOpenFan"
                if name.hasPrefix("uOpenFan") {
                    let fan = DiscoveredFan(
                        name: name.replacingOccurrences(of: "uOpenFan-", with: ""),
                        hostname: name
                    )
                    discoveredFans.append(fan)
                }
            }
        }
        
        onFansDiscovered?(discoveredFans)
    }
    
    deinit {
        browser?.cancel()
    }
}