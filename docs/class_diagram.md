# Diagrama de classes

```mermaid
classDiagram
    class User {
      +int id
      +string username
      +string email
      +string hashed_password
      +string token
    }
    class PasswordResetToken {
      +int id
      +int user_id
      +string token_hash
      +datetime expires_at
      +datetime used_at
    }
    class Friendship {
      +int id
      +int requester_id
      +int addressee_id
      +FriendshipStatus status
    }
    class Folder {
      +int id
      +string name
      +FolderVisibility visibility
      +int author_id
      +int parent_folder_id
    }
    class Page {
      +int id
      +string title
      +PageStatus status
      +PageVisibility visibility
      +int author_id
      +int folder_id
    }
    class PageShare {
      +int page_id
      +int user_id
      +PageSharePermission permission
    }
    class PageBlock {
      +int id
      +int page_id
      +PageBlockType block_type
      +string content
      +int position
    }
    class Comment {
      +int id
      +int page_id
      +int author_id
      +int parent_comment_id
      +string body
      +bool is_deleted
    }
    class CodeExample {
      +int id
      +int page_id
      +int author_id
      +string code
      +bool is_public
    }
    class Language
    class Tag
    class PageTagLink

    User "1" --> "*" PasswordResetToken
    User "1" --> "*" Folder : owns
    User "1" --> "*" Page : authors
    User "1" --> "*" Comment : authors
    User "1" --> "*" CodeExample : authors
    User "1" --> "*" Friendship : requester/addressee
    Folder "0..1" --> "*" Folder : parent
    Folder "0..1" --> "*" Page : contains
    Page "1" --> "*" PageBlock
    Page "1" --> "*" Comment
    Page "1" --> "*" CodeExample
    Page "1" --> "*" PageShare
    User "1" --> "*" PageShare
    Language "0..1" --> "*" Page
    Page "*" --> "*" Tag : PageTagLink
```

As regras de acesso não ficam espalhadas nas classes: são centralizadas em `app/permissions.py`, que combina autoria, amizade, compartilhamento específico e privacidade hierárquica das pastas.
