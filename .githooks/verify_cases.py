# checks if the specified fragments (4 fragments) are identical in two files:
# (the original file and the comparison file passed as a parameter)
# Run this script from the command line with:
# python verify_cases.py original_file.py comparison_file.py


import sys


def read_file_lines(filepath):
    """ Read all lines from a file """
    with open(filepath, "r") as file:
        return file.readlines()


def find_line_index(lines, target):
    """ Find the index of the first line that matches the target """
    for i, line in enumerate(lines):
        if line.strip() == target:
            return i
    return -1


def collect_valid_lines(lines, start, end, valid_prefixes=None):
    """
    Collect lines between start and end indices, and check if they match the allowed prefixes.
    Only allow empty lines or lines starting with any prefix in `valid_prefixes`.
    """
    filtered_lines = []
    for line in lines[start:end]:
        stripped_line = line.strip()
        if stripped_line == "" or (
                valid_prefixes and any(stripped_line.startswith(prefix) for prefix in valid_prefixes)):
            continue
        else:
            filtered_lines.append(stripped_line)
    return filtered_lines

#################


def verify_lines(lines_template, lines_to_verify, comparison_file, verbose=False):
    all_fragments_identical = True

    # 1. Check fragment from line 1 to 15
    if lines_template[:15] != lines_to_verify[:15]:
        differing_lines1 = [i + 1 for i in range(15) if
                            lines_template[i].strip() and lines_template[i] != lines_to_verify[i] and
                            lines_template[i] not in lines_to_verify[:15]]
        if verbose:
            print(f"Error1: line {differing_lines1} is not identical in {comparison_file}.")
        else:
            print(f"Error1: file {comparison_file} is not identical.")
            print(f"- {differing_lines1}")
        all_fragments_identical = False
    else:
        if verbose:
            print("Fragment 1 (lines 1-15) is identical")

    # 2. Check lines from line 16 to "def CaseArgumentParser():"
    start_line = 16
    end_index_original = find_line_index(lines_template, "def CaseArgumentParser():")
    end_index_comparison = find_line_index(lines_to_verify, "def CaseArgumentParser():")

    if end_index_comparison == -1:
        if verbose:
            print(f"Error2:'def CaseArgumentParser():' not found in: {comparison_file}")
        else:
            print(f"Error2: File {comparison_file} is not identical.")
        all_fragments_identical = False

    invalid_lines_original = collect_valid_lines(lines_template, start_line - 1, end_index_original,
                                                 ["import", "from"])
    invalid_lines_comparison = collect_valid_lines(lines_to_verify, start_line - 1, end_index_comparison,
                                                   ["import", "from"])

    if invalid_lines_original or invalid_lines_comparison:
        if verbose:
            print("Error2: (lines till 'def CaseArgumentParser():') contains invalid lines:")
            print(f"################# Lines in original file: ################# \n {invalid_lines_original}")
            print(f"################# Invalid lines in comparison file: ################# \n {invalid_lines_comparison}")
        else:
            print(
                f"Error2: File {comparison_file} is not identical. Wrong lines: {invalid_lines_comparison}")
        all_fragments_identical = False
    if verbose:
        print("Fragment 2 is identical.")

    # 3. Check fragment from 'def CaseArgumentParser():' to '# Other arguments...'
    start_line_fragment_3_original = find_line_index(lines_template, "def CaseArgumentParser():")
    start_line_fragment_3_comparison = find_line_index(lines_to_verify, "def CaseArgumentParser():")
    end_line_fragment_3_original = find_line_index(lines_template, "# Other arguments needed for this specific case, "
                                                                    "PARSE CASE SPECIFIC ARGUMENTS UNDER THIS LINE:")
    end_line_fragment_3_comparison = find_line_index(lines_to_verify, "# Other arguments needed for this specific "
                                                                      "case, PARSE CASE SPECIFIC ARGUMENTS UNDER THIS"
                                                                      " LINE:")

    if end_line_fragment_3_comparison == -1:
        if verbose:
            print(f"Error3: '# Other arguments needed for this specific case' not found in {comparison_file}.")
        # else:
        #     print(f"Error: file {comparison_file} not identical")
        all_fragments_identical = False
    else:
        fragment_3_original = lines_template[start_line_fragment_3_original:end_line_fragment_3_original]
        fragment_3_comparison = lines_to_verify[start_line_fragment_3_comparison:end_line_fragment_3_comparison]

        if fragment_3_original != fragment_3_comparison:
            if verbose:
                print("Error3: ('def CaseArgumentParser():' to '# Other arguments...') is not identical.")
                print(f"################# Lines in original file: ################# \n {fragment_3_original}")
                print(f"################# Invalid lines in comparison file: ################# \n {fragment_3_comparison}")
            else:
                print(
                    f"Error3: File {comparison_file} is not identical. ################# Wrong lines "
                    f"################# \n = {fragment_3_comparison}")
            all_fragments_identical = False
        else:
            if verbose:
                print("Fragment 3 is identical.")

    # 4. New fragment from "# Other arguments needed for this specific case" to "return parser"
    start_line_fragment_4_original = find_line_index(lines_template, "# Other arguments needed for this specific "
                                                                     "case, PARSE CASE SPECIFIC ARGUMENTS UNDER THIS "
                                                                     "LINE:")
    start_line_fragment_4_comparison = find_line_index(lines_to_verify, "# Other arguments needed for this specific "
                                                                        "case, PARSE CASE SPECIFIC ARGUMENTS UNDER "
                                                                        "THIS LINE:")
    end_line_fragment_4_original = find_line_index(lines_template, "return parser")
    end_line_fragment_4_comparison = find_line_index(lines_to_verify, "return parser")

    if start_line_fragment_4_comparison == -1 or end_line_fragment_4_comparison == -1:
        if verbose:
            print(f"Error4: markers not found in {comparison_file}.")
        all_fragments_identical = False
    else:
        # Collect valid lines for both files (ignoring empty lines or lines starting with "parser.")
        filtered_original = collect_valid_lines(lines_template, start_line_fragment_4_original + 1,
                                                end_line_fragment_4_original, valid_prefixes=["parser."])
        filtered_comparison = collect_valid_lines(lines_to_verify, start_line_fragment_4_comparison + 1,
                                                  end_line_fragment_4_comparison, valid_prefixes=["parser."])

        if filtered_original != filtered_comparison:
            all_fragments_identical = False
            if verbose:
                print(f"Error4: file {comparison_file} is not identical.")
                print("################# Lines in original file: ################# \n")
                print("\n".join(filtered_original))
                print("################# Invalid lines in comparison file: ################# \n")
                print("\n".join(filtered_comparison))
            else:
                print(f"Error4 in {comparison_file}")
                print("################# Invalid lines in comparison file: #################")
                print("\n".join(filtered_comparison))
        else:
            if verbose:
                print("Fragment 4 is identical.")

        # 5. Check fragment from "def CaseRun(args):" to "# Other parameters used by this particular case"
        start_line_fragment_5_original = find_line_index(lines_template, "def CaseRun(args):")
        start_line_fragment_5_comparison = find_line_index(lines_to_verify, "def CaseRun(args):")
        end_line_fragment_5_original = find_line_index(lines_template,
                                                       "# Other parameters used by this particular case")
        end_line_fragment_5_comparison = find_line_index(lines_to_verify,
                                                         "# Other parameters used by this particular case")

        if start_line_fragment_5_original == -1 or end_line_fragment_5_original == -1:
            if verbose:
                print("Error5: markers not found in the original file.")
        elif start_line_fragment_5_comparison == -1 or end_line_fragment_5_comparison == -1:
            if verbose:
                print("Error5: markers not found in the comparison file.")
            all_fragments_identical = False
        else:
            # Collect the full fragment, including the start and end lines
            fragment_5_original = lines_template[start_line_fragment_5_original:end_line_fragment_5_original + 1]
            fragment_5_comparison = lines_to_verify[
                                    start_line_fragment_5_comparison:end_line_fragment_5_comparison + 1]

            if fragment_5_original != fragment_5_comparison:
                all_fragments_identical = False
                if verbose:
                    print("Error5: from ('def CaseRun(args):' to '# Other parameters used by this particular "
                          "case' is not identical.")
                    print("################# Lines in original file: #################")
                    print("".join(fragment_5_original))
                    print("################# Invalid lines in comparison file: ################# \n")
                    print("".join(fragment_5_comparison))
                else:
                    print(f"Error5: File {comparison_file} is not identical.")
            else:
                if verbose:
                    print("Fragment 5 is identical.")

    if all_fragments_identical:
        return True
    else:
        print(f"Error: File {comparison_file} is not identical.")
        return False


# def compare_lines(template_lines, provided_lines):
#     """
#     Compare two arrays of lines, identifying mismatches and missing lines.
#
#     Args:
#         template_lines (list): Reference array of lines
#         provided_lines (list): Array of lines to compare against template
#
#     Returns:
#         bool: True if arrays match, False if differences found
#     """
#     issues = []
#     template_idx = 0
#     provided_idx = 0
#
#     while template_idx < len(template_lines) and provided_idx < len(provided_lines):
#         template_line = template_lines[template_idx].strip()
#         provided_line = provided_lines[provided_idx].strip()
#
#         # Check for matching lines
#         if template_line == provided_line:
#             template_idx += 1
#             provided_idx += 1
#             continue
#
#         # Look ahead for potential moved lines
#         found_match = False
#         lookahead = 1
#         while provided_idx + lookahead < len(provided_lines):
#             if template_line == provided_lines[provided_idx + lookahead].strip():
#                 found_match = True
#                 # Report skipped lines
#                 for i in range(lookahead):
#                     issues.append(f"Unexpected line at position {provided_idx + i + 1}: {provided_lines[provided_idx + i]}")
#                 provided_idx += lookahead
#                 break
#             lookahead += 1
#
#         if not found_match:
#             issues.append(f"Mismatch at line {provided_idx + 1}: Expected '{template_line}', got '{provided_line}'")
#             template_idx += 1
#             provided_idx += 1
#
#     # Check for missing lines at the end
#     while template_idx < len(template_lines):
#         issues.append(f"Missing line at position {provided_idx + 1}: Expected '{template_lines[template_idx].strip()}'")
#         template_idx += 1
#
#     # Check for extra lines at the end
#     while provided_idx < len(provided_lines):
#         issues.append(f"Extra line at position {provided_idx + 1}: '{provided_lines[provided_idx].strip()}'")
#         provided_idx += 1
#
#     # Print all issues if any found
#     if issues:
#         print("\nFound differences:")
#         for issue in issues:
#             print(issue)
#         return False
#
#     return True


def verify_file(original_file, comparison_file):
    """ Verify fragments in the files are identical """
    original_lines = read_file_lines(original_file)
    comparison_lines = read_file_lines(comparison_file)
    output = verify_lines(original_lines, comparison_lines, comparison_file)
    # output = comparison_lines(original_lines, comparison_lines)
    return output


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <original_file> <comparison_file>")
        sys.exit(1)

    original_file_path = sys.argv[1]
    comparison_file_path = sys.argv[2]
    result = verify_file(original_file_path, comparison_file_path)
    if result:
        print("All fragments are identical")
    # else:
    #    print(f"File {comparison_file_path} is not identical.")
