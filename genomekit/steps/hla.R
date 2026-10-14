# HLA typing with HIBAG (European pre-fit model, hg19) from the imputed MHC region.
# Usage: Rscript hla.R <mhc.bed prefix> <model.RData> <out.tsv>
args <- commandArgs(TRUE)
suppressMessages(library(HIBAG))
g <- hlaBED2Geno(paste0(args[1], ".bed"), paste0(args[1], ".fam"), paste0(args[1], ".bim"), assembly = "hg19", rm.invalid.allele = TRUE, verbose = FALSE)
ml <- get(load(args[2]))
res <- list()
for (locus in names(ml)) {
  m <- hlaModelFromObj(ml[[locus]])
  p <- hlaPredict(m, g, type = "response+prob", match.type = "Position", verbose = FALSE)
  v <- p$value
  pr <- p$postprob[, 1]; top <- head(sort(pr, decreasing = TRUE), 3)
  res[[locus]] <- data.frame(locus = locus, allele1 = v$allele1, allele2 = v$allele2, prob = round(v$prob, 4),
                             matching = if (!is.null(v$matching)) signif(v$matching, 3) else NA,
                             alternatives = paste(sprintf("%s (%.2f)", names(top), top), collapse = "; "))
  hlaClose(m)
}
out <- do.call(rbind, res); print(out[, 1:5])
write.table(out, args[3], sep = "\t", quote = FALSE, row.names = FALSE)
