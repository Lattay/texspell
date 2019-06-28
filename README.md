# About

TexSpell is a Neovim plugin based on the Python RPC API that provide grammr
checking for TeX/LaTeX documents throught other tools.

It work by striping away all TeX commands from the source and sending the
result to a dedicated tool implemented as a backend.

The conception of the module make it possible to have several backends.
As for now only LanguageTool backend is implemented.

# Installation

You have to use Neovim to be able to use this plugin since it uses its RPC API.

First install the backend you want to use. For languagetool, simply download it
from the [official website](https://languagetool.org/#standalone) and put it
wherever you want.

Also install the [protex](https://github.com/lattay/python-protex) module for
python to clean the TeX sources:
```bash
$ pip install -U protex
```

Then use your favorite method to install this plugin.
If you don't have one have a loop at
[vim-plug](https://github.com/junegunn/vim-plug).

```vim
Plug 'lattay/texspell', {'for': ['tex', 'plaintex']}
```

Then add the following to your *.vimrc* or *.config/nvim/init.vim* (or whatever
script ran at startup):
```vim
let g:texspell_languagetool_path = '/path/to/languagetool/directory/'
let g:texspell_lang = 'fr'  " select your language
```

# Configure

TexSpell have some global variables for configuration.
- *g:texspell_engine*: select the backend, by default 'languagetool'
- *g:texspell_lang*: select the language, by default 'en', you can put whatever
  the backend support.
- *g:texspell_disable* and *b:texspell_disable*: disable at startup, waiting for
  a call to TexSpellEnable

LanguageTool specific options:
- *g:texspell_languagetool_path*: path to the installation directory
- *g:texspell_languagetool_port*: port the server should be bound to

Available commands:
- TexSpellDisable: stop everything, disable checking, clear highlighting etc...
  only TexSpellEnable have effect after this
- TexSpellEnable: restart everything after TexSpellEnable
- TexSpellStart: start whatever need to be started to make the check
- TexSpellCheck: request a check, automatically start everything if
  TexSpellStart have not been used yet
- TexSpellJumpNext, TexSpellJumpPrev: move the cursor to the next/previous error
- TexSpellMessage: Show the message associated with the error under the cursor

Available mappings:
- <Plug>(texspell\_check): perform a check
- <Plug>(texspell\_jump\_next): jump to the next error
- <Plug>(texspell\_jump\_prev): jump to the previous error

Highlighting group:
- TexSpellError: the highlighting group used to mark errors

# Usage

Once everything is installed and configured you just have to open your file and
run a check with TexSpellCheck.

Since the languagetool server is a bit slow I decided not to define
autocommands by default.

However if you want this to behave like most linter you can put the following
in your startup script:
```vim
augroup TexSpell
    autocmd!
    autocmd CursorMoved *.tex exec TexSpellMessage
    autocmd VimEnter *.tex exec TexSpellStart
    autocmd BufWritePost *.tex exec TexSpellCheck
    autocmd BufRead *.tex exec TexSpellCheck
augroup END
```
The checks will be performed when opening the file, and when saving. And the
messages will be shown as soon as the cursor enter an error zone.

# Disclaimer

This is still a work in progress and it have some bugs. If you know how to fix
one of them tell me !

For now everything is quite slow !
I think it is mostly because languagetool is but I do not exclude my own code from the problem yet.
You will see that it takes several seconds before the errors updated after you launched a check and that
neovim take a few more second to quit (waiting for the languagetool server to be killed).

I hope to improve that in the future but if it appear to be mostly because of languagetool I won't be able to do much.

Note however that only one instance hold the server so if you open several instances of neovim,
the other will not be affected by the startup and exit delay of the server.

# Contributing

All contributions are welcomed. If you want to fix a bug or implement a new
backend feel free to submit a pull request.

# TODO

- [ ] Make things more incremental to improve speed. Maybe the best way would be to
  identify paragraphs and do a request for each one, updating highlighting incrementally
- [ ] Prevent errors to mess the screen with overly long messages
- [ ] Implement new backends
  - [ ] grammalecte
