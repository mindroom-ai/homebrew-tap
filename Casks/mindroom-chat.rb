cask "mindroom-chat" do
  version "0"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"

  url "https://github.com/mindroom-ai/mindroom-chat/releases/download/v#{version}/MindRoom-Chat.dmg"
  name "MindRoom Chat"
  desc "Matrix chat client for MindRoom AI agents"
  homepage "https://github.com/mindroom-ai/mindroom-chat"

  # Keep the -mindroom.N suffix; the default regex stops at 4.12.6.
  livecheck do
    url :url
    regex(/^v?(\d+(?:\.\d+)+-mindroom\.\d+)$/i)
    strategy :github_latest
  end

  depends_on macos: :ventura

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
