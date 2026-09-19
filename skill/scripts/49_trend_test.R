# 火灾占比三期 Cochran–Armitage 趋势检验（复现+扩展叶文）
# 数据：叶元兴等(2025) 图2/表2 公开数字；中期=总数反推（84-6-27=51）
# 变体A：叶文原三期；变体B：并入本研究 2025—2026 增量（2016—2026: 30/48）

library(dplyr)

run <- function(fire, total, label) {
  x <- prop.trend.test(fire, total)   # Cochran-Armitage
  cat(label, "\n")
  cat("  占比:", paste0(round(fire/total*100, 2), "%", collapse=" -> "), "\n")
  cat("  X-squared =", round(x$statistic, 3), ", df =", x$parameter, ", P =", format.pval(x$p.value, digits=3), "\n\n")
}

# 变体A：叶文三期（1984—2003, 2004—2015, 2016—2024）
run(c(6, 51, 27), c(25, 109, 42), "A. 叶文三期（复现）")
# 变体B：第三期并入增量（2016—2026）
run(c(6, 51, 30), c(25, 109, 48), "B. 合并库三期（2016—2026 含增量）")
# 变体C：2000 起点口径（第一期裁为 2000—2003 的近似——叶文未给 2000 年前分型，仅作参考不报告）
