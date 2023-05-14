# Export a PDF File To a XLSX File

```$xslt
mvn clean install
```

The sample class ExportPDFToXLSX converts a PDF file to a XLSX file.

```$xslt
mvn -f pom.xml exec:java -Dexec.mainClass=hackathon.pdfprocessor.ExportPDFToXLSX -Dexec.args="files/input.pdf files/output.xlsx"
```
