if ! exists('g:texspell_engine')
    let g:texspell_engine = 'languagetool'
endif
if ! exists('g:texspell_lang')
    let g:texspell_lang = 'fr'
endif

if ! exists('g:texspell_languagetool_path')
    let g:texspell_languagetool_path = '/usr/lib/languagetool/'
endif

if ! exists('g:texspell_languagetool_port')
    let g:texspell_languagetool_port = 8888
endif

hi TexSpellError gui=none guifg=#3C3836 guibg=#FB4934
