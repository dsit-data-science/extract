import re
from math import ceil


def jaccard_similarity(set1: set, set2: set):
    """
    Calculate Jaccard similarity between two sets.

    Args:
        set1 (set): The first set.
        set2 (set): The second set.

    Returns:
        float: The Jaccard similarity between the two sets.
    """

    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    return intersection / union


class PlaintextHolder:
    """
    A class to hold and process plaintext for the purpose of searching and highlighting text.
    """

    SPACE_TOKEN = "<SPACE_TOKEN>"
    NEWLINE_TOKEN = "<NEWLINE_TOKEN>"
    WORD_PATTERN = r"\S+"
    SPACE_PATTERN = r"[^\S\n]+"
    NEWLINE_PATTERN = r"\n+"

    def __init__(self, text: str):
        """
        Initialize the PlaintextHolder object.

        Args:
            text (str): The main piece of text to be stored and processed.
        """
        self.text = text
        self.tokens = self.tokenize()

    @property
    def text(self) -> str:
        """
        Retrieves the raw text stored in the instance.
        Returns:
            str: The raw text.
        """
        return self._text

    @text.setter
    def text(self, value: str):
        """
        Sets the raw text for the instance.

        Args:
            value (str): The text to be set.
        """
        if not isinstance(value, str):
            raise ValueError("Text must be a string.")
        self._text = value
        self.tokens = self.tokenize(value)

    @property
    def tokens(self) -> list[str]:
        """
        Retrieves the tokenized version of the text.

        Returns:
            list[str]: The list of tokens.
        """
        return self._tokens

    @tokens.setter
    def tokens(self, value: list[str]):
        """
        Sets the tokenized version of the text.

        Args:
            value (list[str]): The list of tokens to be set.
        """
        if not isinstance(value, list):
            raise ValueError("Tokens must be a list.")
        self._tokens = value

    def tokenize(self, text: str = None) -> list[str]:
        """
        Tokenizes the input text based on predefined patterns for words, spaces, and newlines.

        Args:
            text (str): The input text to be tokenized.

        Returns:
            List[str]: A list of tokens where each token is a word, space, or newline. Sequences of spaces and newlines are treated as single
                tokens.
        """
        if text is None:
            text = self.text
        if not isinstance(text, str):
            raise ValueError("Text must be a string.")

        # Combine the patterns into one regex
        combined_pattern = f"({self.WORD_PATTERN}|{self.SPACE_PATTERN}|{self.NEWLINE_PATTERN})"

        # Find all matches in the text
        tokens = re.findall(combined_pattern, text)

        # Replace space and newline tokens with <SPACE> and <NEWLINE>
        tokens = [
            self.SPACE_TOKEN
            if re.fullmatch(self.SPACE_PATTERN, token)
            else self.NEWLINE_TOKEN
            if re.fullmatch(self.NEWLINE_PATTERN, token)
            else token
            for token in tokens
        ]

        return tokens

    def convert_tokens_to_string(self, tokens: list[str] = None) -> str:
        """
        Converts the given tokens into text, taking into account the special tokens of the class.

        This method replaces special tokens with their respective characters:
        - SPACE_TOKEN is replaced with a space character.
        - NEWLINE_TOKEN is replaced with a newline character.

        If no tokens are provided, the method uses the instance's tokens attribute.

        Args:
            tokens (list, optional): A list of tokens to process. Defaults to None.

        Returns:
            str: The processed text as a single string.
        """

        if tokens is None:
            tokens = self.tokens
        tokens = [" " if token == self.SPACE_TOKEN else "\n" if token == self.NEWLINE_TOKEN else token for token in tokens]
        return "".join(tokens)

    def get_slice(self, start_idx: int = None, end_idx: int = None) -> list[str]:
        """
        Returns a slice of the tokens list from start_idx to end_idx.

        Parameters:
        start_idx (int, optional): The starting index of the slice. Defaults to 0 if not provided.
        end_idx (int, optional): The ending index of the slice. Defaults to the length of the tokens list if not provided.

        Returns:
        list: A sublist of tokens from start_idx to end_idx.
        """

        if start_idx is None:
            start_idx = 0
        if end_idx is None:
            end_idx = len(self.tokens)

        return self.tokens[start_idx:end_idx]

    def jaccard_similarity_search(
        self,
        text: str,
        threshold: float = 0.0,
        max_results: int = 1,
        case_sensitive: bool = False,
        ignore_whitespace: bool = True,
        vary_window_size: bool = False,
    ) -> list[dict]:
        """
        Perform a Jaccard similarity search on the given text against the source tokens.

        Args:
            text (str): The text to search for.
            threshold (float, optional): The minimum similarity score to consider a match. Must be between 0 and 1. Defaults to 0.0.
            max_results (int, optional): The maximum number of results to return. Defaults to 1.
            case_sensitive (bool, optional): Whether to consider case when comparing tokens. Defaults to False.
            ignore_whitespace (bool, optional): Whether to ignore whitespace tokens in the comparison. Defaults to True.
            vary_window_size (bool, optional): Whether to allow varying window sizes for the search. Defaults to False.

        Returns:
            list[dict]: A list of dictionaries containing the slice indices, tokens, and similarity score for each match that meets the
                threshold.
        """

        if threshold is None:
            threshold = 0.0
        elif threshold < 0 or threshold > 1:
            raise ValueError("Threshold must be between 0 and 1.")

        source_tokens = self.tokens.copy()
        search_tokens = self.tokenize(text)
        if not case_sensitive:
            source_tokens = [token.lower() for token in source_tokens]
            search_tokens = [token.lower() for token in search_tokens]

        base_window_size = len(search_tokens)
        search_token_set = set(search_tokens) - {self.SPACE_TOKEN, self.NEWLINE_TOKEN} if ignore_whitespace else set(search_tokens)

        similarities = []
        for i in range(len(source_tokens) - base_window_size + 1):
            token_slice = source_tokens[i : i + base_window_size]
            window_token_set = set(token_slice) - {self.SPACE_TOKEN, self.NEWLINE_TOKEN} if ignore_whitespace else set(token_slice)
            similarity = jaccard_similarity(search_token_set, window_token_set)
            similarities.append((i, similarity))

        similarities = sorted(similarities, key=lambda x: x[-1], reverse=True)[:max_results]

        results = []
        for i, sim in similarities:
            if sim >= threshold:
                # Calculate 5% before and after the match
                extra_tokens = ceil(base_window_size * 0.05)
                start_idx = max(0, i - extra_tokens)
                end_idx = min(len(source_tokens), i + base_window_size + extra_tokens)
                results.append(
                    {
                        "slice": [start_idx, end_idx],
                        "tokens": self.get_slice(start_idx, end_idx),
                        "score": sim,
                    }
                )

        return results

    def exact_text_search(self, text: str, max_results: int = 1, case_sensitive: bool = False) -> list[dict]:
        """
        Perform an exact text search within the tokenized source text.

        Args:
            text (str): The text to search for within the source tokens.
            max_results (int, optional): The maximum number of results to return. Defaults to 1.
            case_sensitive (bool, optional): Whether the search should be case-sensitive. Defaults to False.

        Returns:
            list: A list of dictionaries containing the slice indices and the corresponding tokens for each match.

        Raises:
            ValueError: If `text` is not a string.
            ValueError: If `max_results` is not None or an integer.
            ValueError: If `max_results` is a negative integer.
        """

        # Input validation
        if not isinstance(text, str):
            raise ValueError("text must be a string.")
        if max_results is not None and not isinstance(max_results, int):
            raise ValueError("max_results must be None or an integer.")
        elif isinstance(max_results, int) and max_results < 0:
            raise ValueError("max_results must be None or a non-negative integer.")
        elif max_results == 0:
            return []

        source_tokens = self.tokens.copy()
        search_tokens = self.tokenize(text)
        if not case_sensitive:
            source_tokens = [token.lower() for token in source_tokens]
            search_tokens = [token.lower() for token in search_tokens]
        window_size = len(search_tokens)

        results = []
        for i in range(len(source_tokens) - window_size + 1):
            token_slice = source_tokens[i : i + window_size]
            if token_slice == search_tokens:
                results.append({"slice": [i, i + window_size], "tokens": self.get_slice(i, i + window_size)})

        return results[:max_results]

    def mark_text(self, search_results: list[dict], start_tag: str = "<mark>", end_tag: str = "</mark>", reverse: bool = False) -> str:
        """
        Surround parts of the text with start and end tags to highlight them.

        Args:
            search_results (list[dict]): List of dictionaries each containing a "slice" element (start_idx, end_idx) of the search result.
                                            The slice indices must be within the token list.
            start_tag (str, optional): The tag to start highlighting. Defaults to "<mark>".
            end_tag (str, optional): The tag to end highlighting. Defaults to "</mark>".
            reverse (bool, optional): If True, the text outside rather than inside the search results will be highlighted. Defaults to False.

        Raises:
            ValueError: If search_results is not a list of dictionaries with 'slice' key.

        Returns:
            str: The processed text with highlighted sections.
        """

        # Input validation
        if not all(isinstance(result, dict) and "slice" in result for result in search_results):
            raise ValueError("search_results must be a list of dictionaries with 'slice' key.")

        n_tokens = len(self.tokens)

        highlight_map = [0] * n_tokens
        for search_result in search_results:
            start, end = search_result["slice"]
            highlight_map[start:end] = [1] * (end - start)

        if reverse:
            highlight_map = [1 - val for val in highlight_map]

        # wc-like iterating through the search results to surround with mark tags
        if any(highlight_map):
            in_highlight_section = False
            tokens = [""] * n_tokens
            for idx, token in enumerate(self.tokens):
                token_to_add = token
                if highlight_map[idx]:
                    if not in_highlight_section:
                        token_to_add = f"{start_tag}{token_to_add}"
                        in_highlight_section = True
                    if idx == n_tokens - 1 or not highlight_map[idx + 1]:
                        token_to_add = f"{token_to_add}{end_tag}"
                        in_highlight_section = False

                tokens[idx] = token_to_add
            return self.convert_tokens_to_string(tokens)
        else:
            return self.convert_tokens_to_string()
