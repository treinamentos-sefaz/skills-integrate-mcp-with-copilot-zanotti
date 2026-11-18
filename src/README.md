# API de Atividades da Mergington High School

Uma aplicação FastAPI super simples que permite aos estudantes visualizar e se inscrever em atividades extracurriculares.

## Funcionalidades

- Visualizar todas as atividades extracurriculares disponíveis
- Professores autenticados podem inscrever e desinscrever estudantes
- Estudantes podem consultar atividades e participantes sem login

## Primeiros Passos

1. Instale as dependências:

   ```
   pip install fastapi uvicorn
   ```

2. Crie uma conta de professor localmente (repita para adicionar mais professores):

   ```
   python src/teacher_accounts.py
   ```

   Informe o nome de usuário e a senha nos prompts. O arquivo `src/teachers.json`
   armazena hashes de senha e não deve ser compartilhado ou enviado ao Git.
   Para usar outro caminho, defina `TEACHERS_FILE` tanto ao criar as contas
   quanto ao iniciar o servidor.

3. Execute a aplicação a partir da raiz do repositório:

   ```
   uvicorn src.app:app
   ```

4. Abra http://localhost:8000. Professores podem entrar pelo ícone de usuário.
   A documentação da API está disponível em http://localhost:8000/docs.

As sessões são armazenadas em memória, expiram após oito horas e são perdidas
ao reiniciar o servidor. Para uma implantação com vários processos ou
instâncias, é necessário armazenamento compartilhado de sessões; use HTTPS
para proteger credenciais e cookies fora do ambiente local.

## Endpoints da API

| Método | Endpoint                                                          | Descrição                                                           |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Obter todas as atividades com seus detalhes e contagem atual de participantes |
| POST   | `/auth/login`                                                     | Autenticar professor com JSON contendo `username` e `password`       |
| GET    | `/auth/session`                                                   | Consultar o estado da sessão                                        |
| POST   | `/auth/logout`                                                    | Encerrar a sessão de professor                                      |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Inscrever estudante (requer sessão de professor)                     |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Desinscrever estudante (requer sessão de professor)              |

As requisições autenticadas de alteração devem enviar o cookie de sessão e o
cabeçalho `X-Requested-With: XMLHttpRequest`.

## Modelo de Dados

A aplicação usa um modelo de dados simples com identificadores significativos:

1. **Atividades** - Usa o nome da atividade como identificador:

   - Descrição
   - Cronograma
   - Número máximo de participantes permitidos
   - Lista de emails de estudantes que estão inscritos

2. **Estudantes** - São identificados pelo email na lista de participantes.

As atividades e inscrições são armazenadas em memória e serão resetadas quando
o servidor reiniciar. As credenciais de professores permanecem no arquivo JSON.
