# Webpage

Webpage is a tool for managing small static website on shared hosting.
No need for database, FTP access, cPanel, Plesk, etc.
You can edit pages and files via web interface and handle backups in one click.

## Installation

There is cpanfile for installing dependencies.
You need SSH access (or some other way) to install required Perl modules.


```bash
cpanm --installdeps --local-lib
```

Clone github repo to hosting root dir:
git clone https://github.com/agrinevich/webpage.git
Set access rights on CGI files to 755.
Create directory cgi-bin/logs.
Create directory for backups outside your public HTML dir.
Create main.conf from main.conf.example and put in cgi-bin dir.
Create .htaccess from .htaccess.example and put in cgi-bin/admin dir.

## Usage

In your browser open website.com/cgi-bin/admin/page.cgi

## License

[MIT](https://choosealicense.com/licenses/mit/)
