# Laboratório descartável

Ferramentas de desenvolvimento para Windows, separadas dos coletores e serviços. Iniciam apenas Redis explicitamente fornecido, com SHA256 fixado, em porta26380 livre, comprovam PID/run_id, testam dados sintéticos e encerram o processo. Não instalar serviço ou usar Redis operacional. A reprodução completa e limitações estão em docs/continuation/implementation_2026-09-10/REPRODUZIR.md.

Executar run.py com Python -I, argumentos explícitos e saída nova sob C:/BRASILEIRAO/work. sitecustomize/lab_guard são injetados somente nos processos do laboratório; não incluir essa pasta no PYTHONPATH de outros usos. kernel_synthetic aguarda a barreira do teste após imports/JIT, antes de assinar Pub/Sub. Os parâmetros são fabricados; não há DB de modelo. A configuração CI usa o mesmo bootstrap contra o Redis descartável do job. Nenhuma dessas ferramentas mede lucro ou comprova execução comercial.
