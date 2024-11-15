import unittest
from git_filtering_internal import tokenize, TokenizationResult, Location, Command

class TestTokenization(unittest.TestCase):
    def test_nested_commands(self):
        subcommands2 = [Command(title="level 3", action="")]
        subcommands1 = [Command(title="level 2", action="", subcommands=subcommands2)]
        commands = [Command(title="subcommands", action="", subcommands=subcommands1)]
        locations = [Location(title="timer", directory="."), Location(title="calc", directory=".")]

        result = tokenize("timer subcommands level 2 level", locations, commands)
        self.assertEqual(result.location.title, "timer")
        self.assertEqual(len(result.commands), 2)
        self.assertEqual(result.commands[0].title, "subcommands")
        self.assertEqual(result.commands[1].title, "level 2")
        self.assertEqual(result.unfinished_query, "level")

    def test_similar_names(self):
        commands = [Command(title="commit", action=""),Command(title="add all & commit", action=""),]
        locations = [Location(title="timer", directory="."), Location(title="calc", directory=".")]

        result = tokenize("timer add all & commit", locations, commands)
        self.assertEqual(result.location.title, "timer")
        self.assertEqual(len(result.commands), 1)
        self.assertEqual(result.commands[0].title, "add all & commit")
        # self.assertEqual(result.commands[1].title, "level 2")
        # self.assertEqual(result.unfinished_query, "level")

if __name__ == '__main__':
    unittest.main()