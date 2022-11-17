## Syahrul-Botak
Tugas Besar `Paling Waras` dari mata kuliah Jaringan Komputer<br>
Implementasi Protokol TCP-like Go-Back-N

> Disclaimer: Nama kelompok tidak mencerminkan kebotakan pihak terkait. Sekian dan terima kasih

## Program Requirement
### Recommended Tools
[WSL](https://learn.microsoft.com/en-us/windows/wsl/install)

### Requirement
- [Git](https://git-scm.com/)
- [Python](https://www.python.org/downloads/)
> Python yang digunakan ketika *development* adalah `3.9`

### How to Run
- Clone repo ini
```
git clone git@github.com:Sister19/jarkom-syahrul-botak.git
cd jarkom-syahrul-botak
```
- Bukalah N terminal untuk menjalankan 1 perintah server dan N-1 client
- Run Server Command
`python server.py [broadcast port] [file path]`
- Run Client Command
`python client.py [client port] [broadcast port] [output path]`

#### Command Example
`python server.py 7000 files/<filename>`
`python client.py 7001 7000 received`
`python client.py 7002 7000 received`

## Author
| NIM      | Nama                       |
|----------|----------------------------|
| 13520059 | Suryanto                   | 
| 13520062 | Rifqi Naufal Abdjul        | 
| 13520161 | M Syahrul Surya Putra      |
