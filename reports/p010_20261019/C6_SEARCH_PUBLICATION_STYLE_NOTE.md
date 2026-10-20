# Original bytes retained

The complete staged whitespace check reported three issues: two existing frozen source copies end with a blank line, and the original failed synthetic-test diff contains a trailing space. These original source/log bytes are retained. The whole-range check did not pass; a separate check excluding exactly these three paths passed. No semantic/runtime claim follows from a whitespace check, and no scientific or test job was repeated for formatting.
