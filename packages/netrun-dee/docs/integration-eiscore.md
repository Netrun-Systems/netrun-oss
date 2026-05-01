# EISCORE (UE5) Integration

Import DEE profiles into Unreal Engine 5.6 for NPC emotional performance using Mass AI, DataTables, and behavior trees.

## Data Import

Three CSVs are provided for UE5 DataTable import:

| File | Contents | UE5 Row Struct |
|------|----------|----------------|
| `DEEProfiles.csv` | 39 profiles with VAD values, category, variants | `FDEEProfileRow` |
| `DEELexicon.csv` | Lexicon patterns with weights per profile | `FDEELexiconRow` |
| `DEEToEISCOREMapping.csv` | Profile-to-EISCORE personality mapping | `FDEEMappingRow` |

Import via UE5 Editor: Content Browser > Import > select CSV > choose matching row struct.

## C++ USTRUCTs

```cpp
USTRUCT(BlueprintType)
struct FDEEProfileRow : public FTableRowBase
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FString ProfileId;       // "DEE-01"

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FString ProfileName;     // "Joy/Happiness"

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    float Valence;           // -1.0 to 1.0

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    float Arousal;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    float Dominance;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FString Category;        // "primary", "secondary", "complex", "additional"
};
```

## Personality-to-DEE Mapping

Map NPC personality archetypes to DEE target profiles:

```cpp
// In NPC initialization
void AEISCORECharacter::InitializeDEEState()
{
    // Look up personality archetype -> DEE targets from DataTable
    FDEEMappingRow* Mapping = DEEMappingTable->FindRow<FDEEMappingRow>(
        PersonalityArchetype, TEXT("DEE Mapping"));

    if (Mapping)
    {
        CurrentDEETargets = Mapping->TargetProfiles;
        BaseValence = Mapping->BaseValence;
        BaseArousal = Mapping->BaseArousal;
    }
}
```

## DEE State in Behavior Trees

Use DEE state as behavior tree conditions:

```cpp
// BTDecorator_DEECheck.cpp
bool UBTDecorator_DEECheck::CalculateRawConditionValue(
    UBehaviorTreeComponent& OwnerComp, uint8* NodeMemory) const
{
    AAIController* Controller = OwnerComp.GetAIOwner();
    AEISCORECharacter* Character = Cast<AEISCORECharacter>(Controller->GetPawn());

    float CurrentIntensity = Character->GetDEEIntensity(TargetProfileId);
    return CurrentIntensity >= IntensityThreshold;
}
```

## Mass AI Emotional Contagion

Spread DEE states between nearby NPCs using Mass AI fragments:

```cpp
// DEEContagionProcessor.cpp — Mass AI processor
void UDEEContagionProcessor::Execute(FMassEntityManager& EntityManager,
    FMassExecutionContext& Context)
{
    // For each entity with DEE state
    EntityManager.ForEachEntityChunk(DEEQuery, Context,
        [](FMassExecutionContext& Context)
    {
        auto DEEStates = Context.GetMutableFragmentView<FDEEStateFragment>();
        auto Transforms = Context.GetFragmentView<FTransformFragment>();

        for (int32 i = 0; i < Context.GetNumEntities(); ++i)
        {
            // Find neighbors within contagion radius
            // Blend neighbor DEE states with decay factor
            // High-arousal emotions spread faster (anger, fear, joy)
            float SpreadFactor = DEEStates[i].Arousal * ContagionRate * DeltaTime;
            // Apply to neighbors...
        }
    });
}
```

## Fragment Definition

```cpp
USTRUCT()
struct FDEEStateFragment : public FMassFragment
{
    GENERATED_BODY()

    UPROPERTY()
    FString ActiveProfileId;    // Current dominant DEE

    UPROPERTY()
    float Valence;

    UPROPERTY()
    float Arousal;

    UPROPERTY()
    float Dominance;

    UPROPERTY()
    float Intensity;            // 0.0 to 3.0

    UPROPERTY()
    float DecayRate;            // How fast this emotion fades
};
```

## Regenerating CSVs

```bash
cd /path/to/netrun-dee
PYTHONPATH=src python3 scripts/eiscore_export.py
```

This produces the three CSVs ready for UE5 DataTable import.
