import { OBJECTIVES, type Objective } from "../../types/analysis";

interface Props {
  value: Objective | "";
  onChange: (value: Objective) => void;
}

export default function ObjectiveSelect({ value, onChange }: Props) {
  return (
    <select id="objective" value={value} onChange={(e) => onChange(e.target.value as Objective)}>
      <option value="" disabled>
        Selecione um objetivo
      </option>
      {OBJECTIVES.map((objective) => (
        <option key={objective} value={objective}>
          {objective}
        </option>
      ))}
    </select>
  );
}
