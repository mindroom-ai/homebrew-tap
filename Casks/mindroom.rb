cask "mindroom" do
  version "2026.10.518"
  sha256 "2e61496061e38709c59bf00d9eb6bc4b71442a6ca502a2900e3e56ddc7504f4e"

  url "https://github.com/mindroom-ai/mindroom/releases/download/v#{version}/MindRoom.dmg"
  name "MindRoom"
  desc "Menu bar app for local MindRoom agent service management"
  homepage "https://github.com/mindroom-ai/mindroom"

  livecheck do
    url :url
    strategy :github_latest
  end

  depends_on arch: :arm64
  depends_on macos: :sonoma

  app "MindRoom.app"

  uninstall launchctl: "chat.mindroom.local",
            quit:      "chat.mindroom.menubar"

  zap trash: [
    "~/Library/LaunchAgents/chat.mindroom.local.plist",
    "~/Library/Logs/mindroom",
    "~/Library/Preferences/chat.mindroom.menubar.plist",
  ]
end
