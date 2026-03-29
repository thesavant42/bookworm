
User Journey: 

As a user of ebook servers looking to expand my knowledge, I want to create an MCP service (FastMCP, STDIO) to search a collection of book servews by keywords, and to download and parse the content via AI.


## Assets: OPDS Servers
-Collect list of OPDS servers, like these, which I will use for testing:
    - http://69.144.163.41:8080/opds
    - https://calibrebooks.dwilliams.cloud/opds
    - http://66.110.246.39:8980/opds

- Each opds xml contains the names of each of the libraries available on that server.

 They can be found by grepping for `title>Library:` in the opds:

```sh
jbras@lilG:/mnt/c/Users/jbras/New folder/bookworm-cli/opds$ grep 'title>Library' *
66-10-246-39-8980-opds.xml:    <title>Library: Calibre_Library</title>
69-144-163-41-8080-opds.xml:    <title>Library: books</title>
calibrebooks-dwilliams-opds.xml:    <title>Library: Computer Books</title>
calibrebooks-dwilliams-opds.xml:    <title>Library: Magazines</title>
calibrebooks-dwilliams-opds.xml:    <title>Library: Regular Books</title>
calibrebooks-dwilliams-opds.xml:    <title>Library: Temp</title>
jbras@lilG:/mnt/c/Users/jbras/New folder/bookworm-cli/opds$ 
```


---

## Search for books

- `http://66.110.246.39:8980/#library_id=Calibre_Library&panel=book_list^search`

### I want to download the Indiana Jones coloring book, so I search for "Indioana Jones" (url encode the spaces and specials)

#### NO MATCH!

- `http://66.110.246.39:8980/#library_id=Calibre_Library&panel=book_list&search=indiana%20jones&sort=timestamp.desc`

-- 8 results, *none* of them what I am looking for.
-- That's ok, let's move on and search the next server.


#### MATCH!

- [`http://69.144.163.41:8080/#library_id=books&panel=book_list&search=indiana%20jones&sort=timestamp.desc`](/69-144-163-41-html.md)
-- This is what I am looking for!
--- `19` reuslts!
    - `http://69.144.163.41:8080/interface-data/books-init?library_id=books&search=indiana%20jones&sort=timestamp.desc&1774765856759`
    - Download links are embedded in the `<span>` of each result.
        - `<span class="button"><a href="/legacy/get/CBR/94036/books/Indiana%20Jones%20Colouring%20Set%20-%20Unknown_94036.cbr">cbr</a></span><div class="data-container">` 


Mope info:
- `https://github.com/goodlibs/calibre-opds-client` - Calibre plugin, does not work as is. May be a good candidate for porting?
