cask "mindroom" do
  version "2026.11.541"
  sha256 "32324f4d7b4b20c3308db8bd6940c8cdc6142c4c3a57799ebc32cdc95fce8cc4"

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
