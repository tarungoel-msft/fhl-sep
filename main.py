import pandas as pd
from pathlib import Path
import openai
from openai.embeddings_utils import get_embedding
from openai.embeddings_utils import cosine_similarity
import subprocess
import glob

DEF_PREFIXES = ['private ', 'public', 'internal']
NEWLINE = '\n'

openai.api_key = '2073fe4c1dc6430dbcc87f39b39dc89e'
openai.api_type = "azure"
openai.api_base = "https://fhlmayjas.openai.azure.com/"
openai.api_version = "2023-05-15"



def get_line_number(filename, linenum = 0):
    found = False

    file1 = open(filename, "r", encoding="utf-8")
    lines = file1.read().splitlines()
    lines = lines[linenum:]
    for line in lines:
        linenum = linenum + 1
        if(check_if_line_has_function(line)):
            print("Function found in file " + filename + " on line: " + linenum.__str__())
            return linenum

    if found == False:
        print("Function not found")
        return linenum

def check_if_line_has_function(line):
    if(line.endswith(")")):
        return True


def process_file(filename, line_num):
    print("opening " + filename + " on line " + str(line_num))

    code = ""
    cnt_braket = 0
    found_start = False
    found_end = False

    with open(filename, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if (i >= (line_num - 1)):
                code += line

                if line.count("{") > 0:
                    found_start = True
                    cnt_braket += line.count("{")

                if line.count("}") > 0:
                    cnt_braket -= line.count("}")

                if cnt_braket == 0 and found_start == True:
                    found_end = True
                    return code


#def get_func():
    # folder = "D:/fhl/Connectors"
    # line_num = 0
    # for filename in glob.iglob(folder + "/*.cs", recursive=True):
    #     line_num = get_line_number(filename, line_num)
    #
    #     if line_num > 0:
    #         process_file(filename, line_num)




def get_function_name(code):
    """
    Extract function name from a line beginning with 'def' or 'async def'.
    """
    for prefix in DEF_PREFIXES:
        if code.startswith(prefix):
            return code[len(prefix): code.index('(')]



def get_until_no_space(all_lines, i):
    """
    Get all lines until a line outside the function definition is found.
    """
    ret = [all_lines[i]]
    for j in range(i + 1, len(all_lines)):
        if len(all_lines[j]) == 0 or all_lines[j][0] in [' ', '\t', ')']:
            ret.append(all_lines[j])
        else:
            break
    return NEWLINE.join(ret)


# def get_functions_python(filepath):
#     """
#     Get all functions in a Python file.
#     """
#     with open(filepath, 'r') as file:
#         all_lines = file.read().replace('\r', NEWLINE).split(NEWLINE)
#         for i, l in enumerate(all_lines):
#             for prefix in DEF_PREFIXES:
#                 if l.startswith(prefix):
#                     code = get_until_no_space(all_lines, i)
#                     function_name = get_function_name(code)
#                     yield {
#                         'code': code,
#                         'function_name': function_name,
#                         'filepath': filepath,
#                     }
#                     break


def get_functions_csharp(filepath):
    """
    Get all functions in a Python file.
    """
    file1 = open(filepath, "r", encoding="utf-8")
    totalLines = len(file1.read().splitlines())
    line_num = 0
    while line_num <= totalLines:
        line_num = get_line_number(filepath, line_num)
        if line_num > 0:
            code = process_file(filepath, line_num)
            if code:
                function_name = get_function_name(code)
                yield {
                    'code': code,
                    'function_name': line_num,
                    'filepath': filepath,
                }
        line_num = line_num + 1


    # with open(filepath, "r", encoding="utf8") as file:
    #     all_lines = file.read().splitlines()
    #     for i, l in enumerate(all_lines):
    #         for prefix in DEF_PREFIXES:
    #             if l.startswith(prefix):
    #                 #code = get_until_no_space(all_lines, i)
    #                 code = process_file(filepath, i)
    #


def extract_functions_from_repo(code_root):
    """
    Extract all .py functions from the repository.
    """
    code_files = list(code_root.glob('**/*.cs'))

    num_files = len(code_files)
    print(f'Total number of .py files: {num_files}')

    if num_files == 0:
        print('Verify openai-python repo exists and code_root is set correctly.')
        return None

    all_funcs = [
        func
        for code_file in code_files
        for func in get_functions_csharp(str(code_file))
    ]

    num_funcs = len(all_funcs)
    print(f'Total number of functions extracted: {num_funcs}')

    return all_funcs




def search_functions(df, code_query, n=3, pprint=True, n_lines=7):
    embedding = get_embedding(code_query, engine='textembeddingada002')
    df['similarities'] = df.code_embedding.apply(lambda x: cosine_similarity(x, embedding))

    res = df.sort_values('similarities', ascending=False).head(n)
    result = []
    if pprint:
        for r in res.iterrows():
            #print(r[1])
            result.append({r[1].filepath, r[1].function_name, round(r[1].similarities, 3)})
            #print(f"{r[1].filepath}:{r[1].function_name}  score={round(r[1].similarities, 3)}")
            #print("\n".join(r[1].code.split("\n")[:n_lines]))
            #print('-' * 70)

    return result


# Set user root directory to the 'openai-python' repository
root_dir = Path.home()

# Assumes the 'openai-python' repository exists in the user's root directory
code_root = root_dir / 'Connectors'

# Extract all functions from the repository
all_funcs = extract_functions_from_repo(code_root)


airbnb_data = pd.read_csv("data/code_search_openai-python.csv")
# View the first 5 rows
airbnb_data.head()


df = pd.DataFrame(all_funcs)
df['code_embedding'] = df['code'].apply(lambda x: get_embedding(x, engine='textembeddingada002'))
df['filepath'] = df['filepath'].map(lambda x: Path(x).relative_to(code_root))
df.to_csv("data/code_search_openai-python.csv", index=False)
df.head()

res = search_functions(df, 'cachedValue = StorageCache.Get(storageCacheToken.Token, objectKey);', n=3)
print(res)


res = search_functions(df, "                HttpWebRequest httpRequest = requestHelper.CreateWebRequest(uri.Authority, uri, context);\n                httpRequest.AllowAutoRedirect = false;\n                httpRequest.Method = \"GET\";\n                httpRequest.Credentials = requestHelper.GetCredentials(url);\n                httpRequest.Timeout = requestHelper.Timeout;", n=3)
print(res)


res = search_functions(df, "           if (DateTime.TryParse(content[ContentProcessingConstants.ParsingMetadataKey][\"ChangeTime\"]?.ToString(), CultureInfo.InvariantCulture, DateTimeStyles.AdjustToUniversal | DateTimeStyles.AssumeUniversal, out DateTime changeTime))\r\n            {\r\n                contentProperties.ChangeTime = changeTime;\r\n            }", n=3)
print(res)