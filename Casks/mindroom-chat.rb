cask "mindroom-chat" do
  version "2026.11.418"
  sha256 "1b34a74dff1c2bbec554649658b8ec93197f9826c795b118b42045b475dcac67"

  url "https://github.com/mindroom-ai/mindroom-chat/releases/download/v#{version}/MindRoom-Chat.dmg"
  name "MindRoom Chat"
  desc "Matrix chat client for MindRoom AI agents"
  homepage "https://github.com/mindroom-ai/mindroom-chat"

  # The newest release that has the DMG, as the updater picks it: a release gets its DMG from a
  # macOS build that ends after it is published, and none when that build fails.
  livecheck do
    url :url
    strategy :github_releases do |json, regex|
      json.map do |release|
        next if release["draft"] || release["prerelease"]
        # MindRoom-Chat.dmg, or MindRoom.dmg for releases from before the rename.
        next unless release["assets"]&.any? { |asset| asset["name"]&.match?(/\AMindRoom(?:-Chat)?\.dmg\z/) }

        release["tag_name"]&.[](regex, 1)
      end
    end
  end

  depends_on macos: :ventura

  # The updater writes this stanza and the url's file name from the release's DMG: MindRoom-Chat.dmg
  # holds MindRoom Chat.app; the MindRoom.dmg of older releases holds MindRoom.app, the name the
  # MindRoom cask's menu bar app also installs as.
  app "MindRoom Chat.app"

  # Leave ~/Library/Containers/chat.mindroom.app: it belongs to the App Store app.
  zap trash: [
    "~/Library/Caches/chat.mindroom.app",
    "~/Library/HTTPStorages/chat.mindroom.app",
    "~/Library/HTTPStorages/chat.mindroom.app.binarycookies",
    "~/Library/Preferences/chat.mindroom.app.plist",
    "~/Library/Saved Application State/chat.mindroom.app~iosmac.savedState",
    "~/Library/WebKit/chat.mindroom.app",
  ]
end
