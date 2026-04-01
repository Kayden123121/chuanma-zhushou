package com.example.ai_assist.utils

object MahjongMapper {
    private val map = mapOf(
        // Man (万)
        "1m" to "🀇", "2m" to "🀈", "3m" to "🀉", "4m" to "🀊", "5m" to "🀋",
        "6m" to "🀌", "7m" to "🀍", "8m" to "🀎", "9m" to "🀏",
        
        // Pin (筒)
        "1p" to "🀙", "2p" to "🀚", "3p" to "🀛", "4p" to "🀜", "5p" to "🀝",
        "6p" to "🀞", "7p" to "🀟", "8p" to "🀠", "9p" to "🀡",
        
        // Sou (索)
        "1s" to "🀐", "2s" to "🀑", "3s" to "🀒", "4s" to "🀓", "5s" to "🀔",
        "6s" to "🀕", "7s" to "🀖", "8s" to "🀗", "9s" to "🀘",
        
        // 字牌（川麻 108 张不用；仅兼容误识别或展示）
        "1z" to "🀀", "2z" to "🀁", "3z" to "🀂", "4z" to "🀃",
        "5z" to "🀆", "6z" to "🀅", "7z" to "🀄"
    )

    fun mapToUnicode(text: String): String {
        // First, expand shorthand notations like "23m" to "2m3m"
        val expandedText = Regex("([0-9]+)([mpsz])").replace(text) { matchResult ->
            val digits = matchResult.groupValues[1]
            val suffix = matchResult.groupValues[2]
            // If it's a single digit (e.g. "1m"), this logic keeps it as "1m"
            // If it's multiple digits (e.g. "23m"), it becomes "2m3m"
            digits.map { "$it$suffix" }.joinToString("")
        }

        var result = expandedText
        // Replace all known codes with their unicode equivalents
        for ((code, unicode) in map) {
            result = result.replace(code, unicode)
        }
        return result
    }

    fun mapListToUnicode(codes: List<String>): List<String> {
        return codes.map { mapToUnicode(it) }
    }
}
