" Default config
let g:texspell_engine = get(g:, 'texspell_engine', 'languagetool')
let g:texspell_lang = get(g:, 'texspell_lang', 'en')
let g:texspell_languagetool_path = get(g:, 'texspell_languagetool_path', '/usr/lib/languagetool/')
let g:texspell_languagetool_port = get(g:, 'texspell_languagetool_port', 8888)

" Default highlighting
hi TexSpellError gui=none guifg=#3C3836 guibg=#FB4934 ctermfg=white ctermbg=red

" Available mappings
noremap <silent> <Plug>(texspell_jump_next) <Cmd>TexSpellJumpNext<CR>
noremap <silent> <Plug>(texspell_jump_prev) <Cmd>TexSpellJumpPrev<CR>
noremap <silent> <Plug>(texspell_check) <Cmd>TexSpellJumpPrev<CR>
