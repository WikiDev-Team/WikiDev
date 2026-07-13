# Diagrama de classes

```mermaid
classDiagram
    class User {
      +id: int
      +username: str
      +email: str
      +display_name: str
      +bio: str
      +avatar_url: str
    }

    class Friendship {
      +id: int
      +requester_id: int
      +addressee_id: int
      +status: FriendshipStatus
      +created_at: datetime
      +updated_at: datetime
    }

    class Page {
      +id: int
      +title: str
      +page_type: PageType
      +status: PageStatus
      +visibility: PageVisibility
      +author_id: int
    }

    class PageShare {
      +page_id: int
      +user_id: int
      +permission: PageSharePermission
    }

    class PageBlock {
      +id: int
      +page_id: int
      +position: int
      +block_type: PageBlockType
      +content: str
    }

    User "1" --> "0..*" Page : author
    User "1" --> "0..*" Friendship : requester
    User "1" --> "0..*" Friendship : addressee
    User "1" --> "0..*" PageShare : receives
    Page "1" --> "0..*" PageShare : grants
    Page "1" --> "0..*" PageBlock : contains
```

## Regras de acesso

- `PRIVATE`: somente o autor.
- `FRIENDS`: autor e amizades aceitas.
- `PUBLIC`: qualquer usuário autenticado.
- `CUSTOM`: autor e usuários presentes em `PageShare`.
- `VIEW`: leitura da página.
- `EDIT`: leitura e edição de metadados/conteúdo; somente o autor controla o compartilhamento e exclui a página.
