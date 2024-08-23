# nsis_change

#### 介绍

用于替换electron中app-$arch.7z压缩包的小脚本。还有bug未解决（多半不会解决）

目前只能替换**修改后的压缩包**小于**应用中的7z压缩包**

7zip工具打开electron使用nsis打包后的exe即可解压应用中的7z压缩包查看大小。

#### 使用

```bash
usage: nsis_change.py [-h] -f FILE [-o OUTPUT] [-x EXTRACT] [--app APP]

Replace nsis exe file

options:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  source nsis exe
  -o OUTPUT, --output OUTPUT
                        replace app output file name
  -x EXTRACT            extract app file name
  --app APP             repalce app.7z
```

#### 示例

```bash
python main.py -f "XXX Setup.exe" --app app-32.7z -o BadSetup.exe
```

