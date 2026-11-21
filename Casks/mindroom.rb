cask "mindroom" do
  version "2026.11.492"
  sha256 "2e72a56896a08481e2124764af8b6c2c337813242d6b6347d0cd8741481b3f27"

  url "https://github.com/mindroom-ai/mindroom/releases/download/v#{version}/MindRoom.dmg"
  name "MindRoom"
  desc "Menu bar app for local MindRoom agent service management"
  homepage "https://github.com/mindroom-ai/mindroom"

  # The newest release that has the DMG, as the updater picks it: a release gets its DMG from a
  # macOS build that ends after it is published, and none when that build fails.
  livecheck do
    url :url
    strategy :github_releases do |json, regex|
      json.map do |release|
        next if release["draft"] || release["prerelease"]
        next unless release["assets"]&.any? { |asset| asset["name"] == "MindRoom.dmg" }

        release["tag_name"]&.[](regex, 1)
      end
    end
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
