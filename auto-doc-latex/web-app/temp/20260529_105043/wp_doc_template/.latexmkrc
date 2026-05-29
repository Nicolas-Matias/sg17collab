$pdf_mode = 1;
$pdflatex = 'pdflatex -interaction=nonstopmode -synctex=1 %O %S';
$biber = 'biber %O %S';
push @generated_exts, 'run.xml';
