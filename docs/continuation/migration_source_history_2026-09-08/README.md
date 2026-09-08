# Fontes históricas preservadas para migração

Esta pasta guarda variantes antigas de ferramentas, testes, patches e definições de build, fora do código ativo da aplicação. Não importar, executar ou aplicar os arquivos daqui como parte da instalação. A preservação não reabre estudos encerrados nem altera agendas, dados ou modelos.

Foram auditadas 1.090 ocorrências de fontes próprias nos backups de sessão/tarefa e nos seis ZIPs mistos: 590 conteúdos únicos por SHA256. Destes, 558 já apareciam nos candidatos tracked/untracked do repositório atual. Dos 32 restantes, quatro existem em blobs alcançáveis pelo commit `4dfdec6804b1c5716e3663b4ffcf9bd3aab411ab` de `main` e 28 foram preservados aqui (171.748 bytes).

`SOURCE_INDEX.json` registra as 43 ocorrências inicialmente ausentes do working tree, as referências aos quatro conteúdos no histórico Git e a origem exata de cada variante arquivada. Os nomes em `files/` usam prefixo de SHA para evitar colisões e caminhos Windows longos. Cada cópia teve tamanho e SHA256 conferidos contra os bytes originais; a extensão ou o nome não autoriza sua execução.

A comparação é exata por bytes, sem normalização de quebras de linha ou análise semântica. A seleção limitou-se a arquivos classificados como fontes próprias; ambientes, dependências, binários compilados e bancos não fazem parte desta coleção. A verificação específica de segredos e a inclusão em commit são etapas separadas da entrega; este arquivo não afirma que já ocorreram.

Complemento da raiz `migracao/` do ZIP original: 9 ocorrências, 9 SHA únicos, 1 já presentes no working tree e 0 presentes em `main`; 8 variantes adicionais foram arquivadas (43.988 bytes). O total desta pasta é de 36 arquivos fonte históricos e 215.736 bytes. O campo `migration_root_supplement` do índice contém nomes, hashes e referências exatas. Scripts descartáveis criados depois da captura original não fazem parte desse complemento.
