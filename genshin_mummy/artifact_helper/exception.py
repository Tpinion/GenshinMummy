from termcolor import colored

from genshin_mummy.artifact_helper.type import EntryType, ArtifactType


class BadExcelHeader(Exception):

    def __str__(self):
        message = (
            f"\n\n{colored('(｡・`ω´･)请不要私自修改模板表头~', 'red')}\n"
            '正确表头是这样的： '
            f"{colored('圣遗物类型条件 | 等级条件 | 星级条件 | 主词条条件 | 副词条条件 | 结果', 'green')}"
        )
        return message


class SheetNotFound(Exception):

    def __str__(self):
        message = (f"\n\n{colored('(｡・`ω´･)至少提供一个Sheet给我吧', 'red')}\n")
        return message


class LossActiveSheet(Exception):

    def __str__(self):
        message = (
            f"\n\n{colored('(｡・`ω´･)你的Excel有多个Sheet=>所以我不知道改用哪个', 'red')}\n"
            f"请把你想要执行的那个Sheet改名成{colored('Active', 'green')}")
        return message


class RowValueError(Exception):

    def __init__(self, line: str, tag: str):
        self.line = line
        self.tag = tag

    def __str__(self):
        message = (f"\n\nExcel第 {colored(self.line, 'blue')} 行的"
                   f" {colored(self.tag, 'blue')} 填写不正确\n")
        return message


class BadArtifactType(RowValueError):

    def __init__(self, artifact_type: str, line: str = '', tag: str = ''):
        super().__init__(line, tag)
        self.artifact_type = artifact_type

    def __str__(self):
        super_message = super().__str__()
        reason = f"[{self.artifact_type}] 不是一个有效的圣遗物类型"
        valid_types = '\n'.join([member.value for member in ArtifactType])
        resolution = f"有效的圣遗物类型是：\n{valid_types}"
        message = (f"{super_message}"
                   f"{colored(reason, 'red')}\n"
                   f"{colored(resolution, 'green')}\n")
        return message


class BadNumberOperator(RowValueError):

    def __init__(self, line: str = '', tag: str = ''):
        super().__init__(line, tag)

    def __str__(self):
        super_message = super().__str__()
        reason = "你可能忘记告知、或者使用了错误条件描述"
        resolution = "对于数值，目前仅支持 > < = 三种条件"
        message = (f"{super_message}"
                   f"{colored(reason, 'red')}\n"
                   f"{colored(resolution, 'green')}\n")
        return message


class BadNumber(RowValueError):

    def __init__(self, line: str = '', tag: str = ''):
        super().__init__(line, tag)

    def __str__(self):
        super_message = super().__str__()
        reason = "你可能提供的似乎并不是一个数字"
        message = (f"{super_message}"
                   f"{colored(reason, 'red')}\n")
        return message


class BadSeparator(RowValueError):

    def __init__(self, line: str = '', tag: str = ''):
        super().__init__(line, tag)

    def __str__(self):
        super_message = super().__str__()
        reason = "你可能忘记告知、或者使用了错误条件描述"
        resolution = "对于词条，目前仅支持 有 没有 两种条件"
        message = (f"{super_message}"
                   f"{colored(reason, 'red')}\n"
                   f"{colored(resolution, 'green')}\n")
        return message


class RedundantMainEntryType(RowValueError):

    def __init__(self, line: str = '', tag: str = ''):
        super().__init__(line, tag)

    def __str__(self):
        super_message = super().__str__()
        reason = "主词条只能配置一个条件哦~"
        message = (f"{super_message}"
                   f"{colored(reason, 'red')}\n")
        return message


class BadEntryOperator(RowValueError):

    def __init__(
        self,
        pos_op: str,
        neg_op: str,
        line: str = '',
        tag: str = '',
    ):
        super().__init__(line, tag)
        self.pos_op = pos_op
        self.neg_op = neg_op

    def __str__(self):
        super_message = super().__str__()
        reason = "你可能忘记告知、或者使用了错误条件描述"
        resolution = f"请在{self.tag}前，用 [{self.pos_op}] 或者 [{self.neg_op}] 来约束"
        example = "例如：有元素充能效率，没有防御力百分比"
        message = (f"{super_message}"
                   f"{colored(reason, 'red')}\n"
                   f"{colored(resolution, 'green')}\n"
                   f"{example}")
        return message


class BadEntryType(RowValueError):

    def __init__(self, entry_type: str, line: str = '', tag: str = ''):
        super().__init__(line, tag)
        self.entry_type = entry_type

    def __str__(self):
        super_message = super().__str__()
        reason = f"[{self.entry_type}] 不是一个有效的词条类型"
        valid_types = '\n'.join([member.value for member in EntryType])
        resolution = f"有效的词条类型是：\n{valid_types}"
        message = (f"{super_message}"
                   f"{colored(reason, 'red')}\n"
                   f"{colored(resolution, 'green')}\n")
        return message


class BadConclusion(RowValueError):

    def __init__(self, conclusion: str, line: str = '', tag: str = ''):
        super().__init__(line, tag)
        self.conclusion = conclusion

    def __str__(self):
        super_message = super().__str__()
        reason = f"[{self.conclusion}] 不是一个有效的结论"
        resolution = "结论只有两种可选：锁 或者 不锁"
        message = (f"{super_message}"
                   f"{colored(reason, 'red')}\n"
                   f"{colored(resolution, 'green')}\n")
        return message
