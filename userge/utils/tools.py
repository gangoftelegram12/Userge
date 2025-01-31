# pylint: disable=missing-module-docstring
#
# Copyright (C) 2020-2021 by UsergeTeam@Github, < https://github.com/UsergeTeam >.
#
# This file is part of < https://github.com/UsergeTeam/Userge > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/UsergeTeam/Userge/blob/master/LICENSE >
#
# All rights reserved.

import re
import shlex
import asyncio
from os.path import basename, splitext, join, exists
from emoji import get_emoji_regexp
from typing import Tuple, List, Optional

from html_telegraph_poster import TelegraphPoster
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import userge

_LOG = userge.logging.getLogger(__name__)
_BTN_URL_REGEX = re.compile(r"(\[([^\[]+?)]\[buttonurl:/{0,2}(.+?)(:same)?])")


def sort_file_name_key(file_name: str) -> float:
    if not isinstance(file_name, str):
        raise TypeError(f"Invalid type provided: {type(file_name)}")

    prefix, suffix = splitext(file_name)

    val = 0.0
    inc = 2

    i = 0
    for c in list(prefix)[::-1]:
        if not c.isdigit():
            i += inc
        val += ord(c) * 10 ** i

    i = 0
    for c in list(suffix):
        if not c.isdigit():
            i += inc
        val += ord(c) * 10 ** i

    return val


def demojify(string: str) -> str:
    """ Remove emojis and other non-safe characters from string """
    return get_emoji_regexp().sub(u'', string)


def get_file_id_of_media(message: 'userge.Message') -> Optional[str]:
    """ get file_id """
    file_ = message.audio or message.animation or message.photo \
        or message.sticker or message.voice or message.video_note \
        or message.video or message.document
    if file_:
        return file_.file_id
    return None


def humanbytes(size: float) -> str:
    """ humanize size """
    if not size:
        return ""
    power = 1024
    t_n = 0
    power_dict = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        t_n += 1
    return "{:.2f} {}B".format(size, power_dict[t_n])


def time_formatter(seconds: float) -> str:
    """ humanize time """
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "")
    return tmp[:-2]


# https://github.com/UsergeTeam/Userge-Plugins/blob/master/plugins/anilist.py
def post_to_telegraph(a_title: str, content: str) -> str:
    """ Create a Telegram Post using HTML Content """
    post_client = TelegraphPoster(use_api=True)
    auth_name = "@theUserge"
    post_client.create_api_token(auth_name)
    post_page = post_client.post(
        title=a_title,
        author=auth_name,
        author_url="https://t.me/theUserge",
        text=content
    )
    return post_page['url']


async def runcmd(cmd: str) -> Tuple[str, str, int, int]:
    """ run command in terminal """
    args = shlex.split(cmd)
    process = await asyncio.create_subprocess_exec(*args,
                                                   stdout=asyncio.subprocess.PIPE,
                                                   stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    return (stdout.decode('utf-8', 'replace').strip(),
            stderr.decode('utf-8', 'replace').strip(),
            process.returncode,
            process.pid)


async def take_screen_shot(video_file: str, duration: int, path: str = '') -> Optional[str]:
    """ take a screenshot """
    _LOG.info('[[[Extracting a frame from %s ||| Video duration => %s]]]', video_file, duration)
    ttl = duration // 2
    thumb_image_path = path or join(userge.Config.DOWN_PATH, f"{basename(video_file)}.jpg")
    command = f'''ffmpeg -ss {ttl} -i "{video_file}" -vframes 1 "{thumb_image_path}"'''
    err = (await runcmd(command))[1]
    if err:
        _LOG.error(err)
    return thumb_image_path if exists(thumb_image_path) else None


def parse_buttons(markdown_note: str) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    """ markdown_note to string and buttons """
    prev = 0
    note_data = ""
    buttons: List[Tuple[str, str, bool]] = []
    for match in _BTN_URL_REGEX.finditer(markdown_note):
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and markdown_note[to_check] == "\\":
            n_escapes += 1
            to_check -= 1
        if n_escapes % 2 == 0:
            buttons.append((match.group(2), match.group(3), bool(match.group(4))))
            note_data += markdown_note[prev:match.start(1)]
            prev = match.end(1)
        else:
            note_data += markdown_note[prev:to_check]
            prev = match.start(1) - 1
    note_data += markdown_note[prev:]
    keyb: List[List[InlineKeyboardButton]] = []
    for btn in buttons:
        if btn[2] and keyb:
            keyb[-1].append(InlineKeyboardButton(btn[0], url=btn[1]))
        else:
            keyb.append([InlineKeyboardButton(btn[0], url=btn[1])])
    return note_data.strip(), InlineKeyboardMarkup(keyb) if keyb else None
