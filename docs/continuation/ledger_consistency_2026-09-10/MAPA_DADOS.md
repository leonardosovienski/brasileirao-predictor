# Dados e fontes LGC

Não houve nova aquisição nem leitura de dados operacionais. Os fixtures dos testes e do laboratório são inteiramente sintéticos. Datas de 2024 não são observações históricas reais. As evidências comerciais e bloqueios permanecem no [mapa CLO](../closeout_2026-09-10/MAPA_DADOS.md).

Registros bancários exigem JSON estrito, kind conhecido, valor/unidade positivos finitos, moeda declarada e timestamp com offset. Apostas importadas exigem mercado, seleção, período e linha coerentes. O código não preenche contrato ausente, não autentica o operador e não altera registros antigos. Publicação, recebimento de preço, aceite, custo pessoal e câmbio continuam desconhecidos para o ledger manual; não devem ser inferidos de logged_at/recorded_at.
