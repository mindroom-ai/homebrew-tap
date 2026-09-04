cask "mindroom" do
  version "2026.9.21"
  sha256 "5bc25518f1db8721841d2b4757332fc4fac73e81392cd9ec0a229d2b8c9f57c6"

  url "https://github.com/mindroom-ai/mindroom/releases/download/v#{version}/MindRoom.dmg"
  name "MindRoom"
  desc "Menu bar app for local MindRoom agent service management"
  homepage "https://github.com/mindroom-ai/mindroom"

  livecheck do
    url :url
    strategy :github_latest
  end

  depends_on macos: :ventura

  app "MindRoom.app"

  uninstall launchctl: "chat.mindroom.local",
            quit:      "chat.mindroom.menubar"

  zap trash: [
    "~/Library/LaunchAgents/chat.mindroom.local.plist",
    "~/Library/Logs/mindroom",
    "~/Library/Preferences/chat.mindroom.menubar.plist",
  ]
end
