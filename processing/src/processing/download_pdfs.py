from remotezip import RemoteZip

def main():
    url = "https://open-data-set.oss-cn-beijing.aliyuncs.com/dataset/pdf11000.zip"
    with RemoteZip(url) as z:
        all_files = z.namelist()
        for file_name in all_files[1999:4000]:
            z.extract(file_name, path='./pdfs')

if __name__ == "__main__":
    main()
