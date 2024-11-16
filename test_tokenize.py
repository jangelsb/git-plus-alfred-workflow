import unittest
from git_filtering_internal import tokenize, TokenizationResult, Location, Command

class TestTokenization(unittest.TestCase):
    # def test_nested_commands(self):
    #     subcommands2 = [Command(title="level 3", action="")]
    #     subcommands1 = [Command(title="level 2", action="", subcommands=subcommands2)]
    #     commands = [Command(title="subcommands", action="", subcommands=subcommands1)]
    #     locations = [Location(title="timer", directory="."), Location(title="calc", directory=".")]
    #
    #     result = tokenize("timer subcommands level 2 level", locations, commands)
    #     self.assertEqual(result.location.title, "timer")
    #     self.assertEqual(len(result.commands), 2)
    #     self.assertEqual(result.commands[0].title, "subcommands")
    #     self.assertEqual(result.commands[1].title, "level 2")
    #     self.assertEqual(result.unfinished_query, "level")

    def test_similar_names(self):

        # arrange
        commands = [Command(title="commit", action=""),Command(title="add all & commit", action=""),]
        locations = [Location(title="timer", directory="."), Location(title="calc", directory=".")]

        # act
        result = tokenize("timer add all & commit hi", locations, commands)

        # assert
        self.assertEqual(result.location.title, "timer")
        self.assertEqual(len(result.commands), 1)
        self.assertEqual(result.commands[0].title, "add all & commit")
        self.assertEqual(result.unfinished_query, "hi")


        # arrange
        commands = [Command(title="add all & commit", action=""), Command(title="commit", action="")]
        locations = [Location(title="timer", directory="."), Location(title="calc", directory=".")]

        # act
        result = tokenize("calc add all & commit something else", locations, commands)

        # assert
        self.assertEqual(result.location.title, "calc")
        self.assertEqual(len(result.commands), 1)
        self.assertEqual(result.commands[0].title, "add all & commit")
        self.assertEqual(result.unfinished_query, "something else")

    def test_similar_names2(self):
        commands = [Command(title="add all & commit", action=""), Command(title="commit", action="")]
        locations = [Location(title="timer", directory="."), Location(title="calc", directory=".")]

        result = tokenize("timer commit hi", locations, commands)
        self.assertEqual(result.location.title, "timer")
        self.assertEqual(len(result.commands), 1)
        self.assertEqual(result.commands[0].title, "commit")
        self.assertEqual(result.unfinished_query, "hi")
        # self.assertEqual(result.commands[1].title, "level 2")
        # self.assertEqual(result.unfinished_query, "level")

    def test_multiple_comands(self):
        commands = [Command(title="subcommands", action=""),Command(title="level 2", action=""),]
        locations = [Location(title="timer", directory="."), Location(title="calc", directory=".")]

        result = tokenize("timer subcommands level 2", locations, commands)
        self.assertEqual(result.location.title, "timer")
        self.assertEqual(len(result.commands), 2)
        self.assertEqual(result.commands[0].title, "subcommands")
        self.assertEqual(result.commands[1].title, "level 2")
        self.assertEqual(result.unfinished_query, "")

    def test_muli_word_locations(self):
        commands = [Command(title="subcommands", action=""),Command(title="level 2", action=""),]
        locations = [Location(title="timer", directory="."), Location(title="timer test", directory=".")]

        result = tokenize("timer test subcommands level 2 s ", locations, commands)
        self.assertEqual(result.location.title, "timer test")
        self.assertEqual(len(result.commands), 2)
        self.assertEqual(result.commands[0].title, "subcommands")
        self.assertEqual(result.commands[1].title, "level 2")
        self.assertEqual(result.unfinished_query, "s")

    def test_similar_names3(self): # git timer bbb feature/blurredBackGround_simple
        commands = [Command(title="bbb", action=""), Command(title="feature/blurredBackGround", action=""),Command(title="feature/blurredBackGround_simple", action=""),]
        locations = [Location(title="timer", directory="."), Location(title="test", directory=".")]

        result = tokenize("timer bbb feature/blurredBackGround_simple", locations, commands)
        self.assertEqual(result.location.title, "timer")
        self.assertEqual(len(result.commands), 2)
        self.assertEqual(result.commands[0].title, "bbb")
        self.assertEqual(result.commands[1].title, "feature/blurredBackGround_simple")
        self.assertEqual(result.unfinished_query, "")

if __name__ == '__main__':
    unittest.main()