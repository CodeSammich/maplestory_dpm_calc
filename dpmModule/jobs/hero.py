from ..kernel import core
from ..kernel.core import VSkillModifier as V
from ..character import characterKernel as ck
from functools import partial
from ..status.ability import Ability_tool
from ..execution.rules import RuleSet, InactiveRule
from . import globalSkill
from .jobbranch import warriors

#TODO : 5차 신스킬 적용
'''히어로 스킬 정리
- 콤보 어택 :: 스택당 공격력 2, 최종뎀10% -> 오더 11% +2%(하이퍼) 보공+2%
- 분노(공30)
- 웨폰 마스터리 (최종뎀 10 + 도끼 뎀5%)
- 피지컬 트레이닝 (주/부 스텟 30)
- 찬스 어택 (크리율 20, 상태이상시 뎀뻥25)
- 인레이지 (최종뎀25, 크뎀 20)
- 컴뱃 마스터리 (방무 50)
- 어파 (공30), 75%(하이퍼적용+15)
- 레블 +20%, 타수+1
'''

#ComboAttack
class ComboAttackWrapper(core.StackSkillWrapper):
    def __init__(self, skill, desfortBuff, vEhc, combat = False):
        super(ComboAttackWrapper, self).__init__(skill, 10)
        self.desfortBuff = desfortBuff
        self.vEhc = vEhc
        self.stack = 10  #Better point!
        self.tick = 12 + combat * 1
        self.instinct = False
        self.set_name_style("%d 만큼 콤보 변화")
    
    def toggle(self, state):
        self.instinct = state
        return core.ResultObject(0, core.CharacterModifier(), 0, 0, sname = self.skill.name, spec = 'graph control')
        
    def toggleController(self, state):
        task = core.Task(self, partial(self.toggle, state))
        return core.TaskHolder(task, name = "인스팅트 토글")
        
    def vary(self, diff):
        if diff > 0:
            chance = 0.8 - self.instinct * 0.5
            chanceDouble = chance * 0.8
            diff = diff * (2 * chanceDouble + chance)
        self.stack += diff
        self.stack = max(min(10,self.stack),0)
        return core.ResultObject(0, core.CharacterModifier(), 0, 0, sname = self.skill.name, spec = 'graph control')

    def get_modifier(self):
        multiplier = (1 + self.instinct * 0.01 * (5 + 0.5*self.vEhc.getV(1,1)))
        return core.CharacterModifier(pdamage = 2 * self.stack * multiplier, 
                                            pdamage_indep = self.tick * (self.stack + self.desfortBuff.is_active() * 6) * multiplier,
                                            att = 2 * self.stack * multiplier)

######   Passive Skill   ######
class JobGenerator(ck.JobGenerator):
    def __init__(self):
        super(JobGenerator, self).__init__()
        self.buffrem = False
        self.jobtype = "str"
        self.ability_list = Ability_tool.get_ability_set('boss_pdamage', 'crit', 'mess')
        self.preEmptiveSkills = 2

    def get_ruleset(self):
        ruleset = RuleSet()
        ruleset.add_rule(InactiveRule('콤보 데스폴트', '콤보 인스팅트'), RuleSet.BASE)
        ruleset.add_rule(InactiveRule('레이지 업라이징', '콤보 인스팅트'), RuleSet.BASE)
        return ruleset


    def get_passive_skill_list(self):
        WeaponMastery = core.InformedCharacterModifier("웨폰 마스터리",pdamage_indep = 10, pdamage = 5)   #도끼 사용
        PhisicalTraining = core.InformedCharacterModifier("피지컬 트레이닝",stat_main = 30, stat_sub = 30)
        
        ChanceAttack = core.InformedCharacterModifier("찬스 어택(패시브)",crit = 20)

        CombatMastery = core.InformedCharacterModifier("컴뱃 마스터리",armor_ignore = 50)
        AdvancedFinalAttack = core.InformedCharacterModifier("어드밴스드 파이널 어택(패시브)",att = 30)
        
        return [WeaponMastery, PhisicalTraining, ChanceAttack, CombatMastery, AdvancedFinalAttack]

    def get_not_implied_skill_list(self):
        WeaponConstant = core.InformedCharacterModifier("무기상수", pdamage_indep = 44)
        Mastery = core.InformedCharacterModifier("숙련도", pdamage_indep = -5)        
        Enrage = core.InformedCharacterModifier("인레이지",pdamage_indep = 25, crit_damage = 20)
        
        return [WeaponConstant, Mastery, Enrage]
        
    def generate(self, vEhc, chtr : ck.AbstractCharacter, combat : bool = False):
        '''
        코강 순서:
        레블 - 파택 - 업라이징 - 샤우트 - 인사이징 - 패닉

        어드밴스드 콤보-리인포스, 보스 킬러 / 어드밴스드 파이널 어택-보너스 찬스 / 레이징 블로우-리인포스, 보너스 어택
        
        콤보 카운터 증가 확률
        64% - 2개
        16% - 1개
        20% - 0개

        인스팅트 시
        24% - 2개
        6%  - 1개
        70% - 0개
        '''
        #combat = True
        ######   Skill   ######
        #Buff skills
        Fury = core.BuffSkill("분노", 0, 200*1000, att = 30, rem = True).wrap(core.BuffSkillWrapper)
        EpicAdventure = core.BuffSkill("에픽 어드벤처", 0, 60*1000, cooltime = 120 * 1000, pdamage = 10).wrap(core.BuffSkillWrapper)
        
        #Damage Skills
        Panic = core.DamageSkill("패닉", 720, 1150, 1, cooltime = 40000).setV(vEhc, 5, 3, False).wrap(core.DamageSkillWrapper)
        PanicBuff = core.BuffSkill("패닉(디버프)", 0, 40000, cooltime = -1, pdamage_indep = 25, rem = False).wrap(core.BuffSkillWrapper)
        
        RaisingBlow = core.DamageSkill("레이징 블로우", 600, 200, 8, modifier = core.CharacterModifier(pdamage = 20)).setV(vEhc, 0, 2, False).wrap(core.DamageSkillWrapper)
        RaisingBlowInrage = core.DamageSkill("레이징 블로우(인레이지)", 600, 215, 6, modifier = core.CharacterModifier(pdamage = 20)).setV(vEhc, 0, 2, False).wrap(core.DamageSkillWrapper)  #이걸 사용함.
        RaisingBlowInrageFinalizer = core.DamageSkill("레이징 블로우(인레이지)(최종타)", 0, 215, 2, modifier = core.CharacterModifier(pdamage = 20, crit = 100)).setV(vEhc, 0, 2, False).wrap(core.DamageSkillWrapper)  #이걸 사용함. 둘을 연결해야 함.
        
        Insizing = core.DamageSkill("인사이징", 660, 576, 4, cooltime = 30 * 1000).setV(vEhc, 4, 2, False).wrap(core.DamageSkillWrapper)    # 오더스 적용 필요함.
        InsizingBuff = core.BuffSkill("인사이징(버프)", 0, 30 * 1000, cooltime = -1, pdamage = 25).wrap(core.BuffSkillWrapper)
        InsizingDot = core.DotSkill("인사이징(도트)", 165, 30 * 1000).wrap(core.SummonSkillWrapper)
    
        AdvancedFinalAttack = core.DamageSkill("어드밴스드 파이널 어택", 0, 170, 3 * 0.75).setV(vEhc, 1, 2, False).wrap(core.DamageSkillWrapper)

        RisingRage = core.DamageSkill("레이지 업라이징", 750, 500, 8, cooltime = 10*1000).setV(vEhc, 2, 2, False).wrap(core.DamageSkillWrapper)

        Valhalla = core.BuffSkill("발할라", 900, 30 * 1000, cooltime = 150 * 1000, crit = 30, att = 50).wrap(core.BuffSkillWrapper)
        SwordOfBurningSoul = core.SummonSkill("소드 오브 버닝 소울", 810, 1000, (315+12*vEhc.getV(0,0)), 6, (60+vEhc.getV(0,0)//2) * 1000, cooltime = 120 * 1000, modifier = core.CharacterModifier(crit = 50)).isV(vEhc, 0, 0).wrap(core.SummonSkillWrapper)
        
        ComboDesfort = core.DamageSkill("콤보 데스폴트", 1260, 800 + 32*vEhc.getV(2,3), 7, cooltime = 20 * 1000).isV(vEhc, 2, 3).wrap(core.DamageSkillWrapper)
        ComboDesfortBuff = core.BuffSkill("콤보 데스폴트(버프)", 0, 5 * 1000, rem = False, cooltime = -1).isV(vEhc, 2, 3).wrap(core.BuffSkillWrapper)
        
        ComboInstinct = core.BuffSkill("콤보 인스팅트", 360, 30 * 1000, cooltime = 240 * 1000, rem = False, red = True).isV(vEhc, 1, 1).wrap(core.BuffSkillWrapper)
        ComboInstinctFringe = core.DamageSkill("콤보 인스팅트 균열", 0, 200 + 8*vEhc.getV(1,1), 18).isV(vEhc, 1, 1).wrap(core.DamageSkillWrapper)
        ComboInstinctOff = core.BuffSkill("콤보 인스팅트 종료", 0, 1, cooltime = -1).wrap(core.BuffSkillWrapper)

        ######   Skill Wrapper   ######
        ComboAttack = ComboAttackWrapper(core.BuffSkill("콤보어택", 0, 999999 * 1000), ComboDesfortBuff, vEhc, combat)
        
        #Final attack type
        ComboInstinct.onAfter(ComboInstinctOff.controller(30 * 1000))
        ComboInstinct.onAfter(ComboAttack.toggleController(True))
        ComboInstinctOff.onAfter(ComboAttack.toggleController(False))
        InstinctFringeUse = core.OptionalElement(ComboInstinct.is_active, ComboInstinctFringe, name = "콤보 인스팅트 여부")
    
        #레이징 블로우
        RaisingBlowInrage.onAfters([InstinctFringeUse, RaisingBlowInrageFinalizer, AdvancedFinalAttack, ComboAttack.stackController(1)])

        RisingRage.onAfters([AdvancedFinalAttack, ComboAttack.stackController(1)])
    
        Insizing.onBefore(ComboAttack.stackController(-1))
        Insizing.onAfters([InsizingBuff, InsizingDot, AdvancedFinalAttack])
    
        ComboDesfort.onBefores([ComboDesfortBuff, ComboAttack.stackController(-6)]) # TODO: 데스폴트 데미지에 콤보 카운터 어떻게 적용되는지 확인 필요
        ComboDesfort.onAfter(AdvancedFinalAttack)
        ComboDesfort.onConstraint(core.ConstraintElement("콤보 6개 이상", ComboAttack, partial(ComboAttack.judge, 6, 1)))

        Panic.onBefore(ComboAttack.stackController(-2))
        Panic.onAfters([PanicBuff, AdvancedFinalAttack])
        
        # 오라 웨폰
        auraweapon_builder = warriors.AuraWeaponBuilder(vEhc, 3, 2)
        for sk in [RaisingBlowInrageFinalizer, ComboDesfort, Panic, Insizing, RisingRage]:
            auraweapon_builder.add_aura_weapon(sk)
        AuraWeaponBuff, AuraWeaponCooltimeDummy = auraweapon_builder.get_buff()

        return(RaisingBlowInrage,
                [globalSkill.maple_heros(chtr.level), globalSkill.useful_sharp_eyes(), globalSkill.useful_wind_booster(), globalSkill.useful_combat_orders(),
                    ComboAttack, Fury, EpicAdventure, Valhalla, 
                    InsizingBuff, InsizingDot, AuraWeaponBuff, ComboDesfortBuff, 
                    ComboInstinct, ComboInstinctOff, PanicBuff,
                    globalSkill.soul_contract()] +\
                [Panic, Insizing, ComboDesfort, RisingRage] +\
                [SwordOfBurningSoul] +\
                [AuraWeaponCooltimeDummy] +\
                [RaisingBlowInrage])