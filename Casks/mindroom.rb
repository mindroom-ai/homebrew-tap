cask "mindroom" do
  version "2026.6.53"
  sha256 "ed4e4b4463db1a43d54f52c1b4f115e8bf009329b2fa418ed62c09e69e12823c"

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
