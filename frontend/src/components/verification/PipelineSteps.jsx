import Icon from '../common/Icon.jsx'
import { PIPELINE } from '../../utils/verification.js'

export default function PipelineSteps({ mode }) {
  return (
    <div className="pipeline">
      <h4 className="panel-heading">
        {mode === 'carag' ? 'Features Used' : 'Features used'}
      </h4>

      <ul>
        {PIPELINE.map((step) => {
          const ran = step.modes.includes(mode)

          return (
            <li
              key={step.key}
              className={ran ? 'ran' : 'skipped'}
            >
              <span
                className="pipeline-icon"
                aria-label={ran ? 'Used' : 'Not used'}
              >
                <Icon
                  name={ran ? 'check' : 'dash'}
                  size={15}
                />
              </span>

              <span className="pipeline-label">
                {step.label}
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}