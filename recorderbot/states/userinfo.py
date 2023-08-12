from .base import StepState, StepStatesGroup


class UserInfo(StepStatesGroup, config_path="configs/userinfo.yaml"):
    # # Just name variables differently
    # name = StepState("1. Please enter Your name", "name")
    # surname = StepState("2. Please enter Your surname", "surname")
    # age = StepState("3. Please enter Your age", "age")

    @classmethod
    def final(cls, data: dict) -> str:
        """the final process to process full data
        data: the full data (should be given in outter procedures)
        return: human readable information of process result
        """
        # TODO: not implemented, maybe use cached data
        with open("temp_save_states.txt", "a+") as f:
            f.write(str(data) + "\n")
