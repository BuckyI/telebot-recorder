# Telegram Recorder Bot

It can work as your personal recorder for diary, template journal to help with positive thinking, gratitude journaling, etc.

2023.10.4: It is just a small project for fun but I've turn to web-based app to work as a recorder (and more).

## How It Works?

### Configuration

Privacy-sensitive configurations are stored in `.env` at the root of the project, which will be loaded by `python-decouple`. The file basically includes configurations for the bot, webdav and proxy configs (if needed).

```plaintext
BOT_USERNAME="@telebot_recorder_bot"
BOT_TOKEN=......

WEBDAV_HOSTNAME="https://dav.jianguoyun.com/dav/SYNC/telegram-bot"
WEBDAV_USERNAME=......
WEBDAV_PASSWORD=......

HTTPS_PROXY=......
HTTP_PROXY=......
ALL_PROXY=......
```

Functional configuration, such as record templates and how bot should work, are placed in `configs/` in yaml format.

### Mechanism

The code uses a state-based approach to guide users to walk through a predefined record template, but it can also be adapted to accommodate more general procedures. For now, the `StepStatesGroup` defines a simple, linear, one-directional procedure. Registered commands are used to enter the starting states and proceed to the next step.

It utilizes a local JSON file as a TinyDB database and employs webdav for data persistance. (For improved functionality, it is recommended to use a proper online database service.")
